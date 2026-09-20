"""The WhatsApp channel, run server-side.

A real deployment receives a Meta webhook (POST) for every customer message and replies through the
WhatsApp Business API. Here the same door exists: `handle_inbound` takes a message the way the webhook
delivers it, everything after that is the real agent, and each reply is appended to a per-(brand line,
customer phone) message log in DynamoDB. The customer's phone UI and the brand's inbox both read that
log; a human agent's reply is just another message in it. Only the last hop (Meta's network) is absent.

Conversation state per chat is one small record:
    idle              nothing open; the next message starts something
    awaiting_product  the customer owns several products; we asked which one (buttons) and kept their message
    bot               a step is out and we're waiting for their reply
    human             handed to a person; the bot stays quiet until the ticket is resolved
"""

import re
from datetime import datetime

from src.domain.catalog import BRAND_SLUGS, brand_for
from src.domain.registration import Registration, warranty_details
from src.agent import agent as agent_mod
from src.storage import get_store
from src.webapp import api_core as core

GREETING = re.compile(r"^\W*(hi+|hello+|hey+|hola|namaste|good (morning|afternoon|evening))\W*$", re.I)
_GENERIC = {"washing", "machine", "ac", "split", "air", "conditioner", "front", "the", "my", "a", "is", "of"}

# Which WhatsApp Business number belongs to which brand (a real deployment reads this from Meta's
# `metadata.display_phone_number`).
BRAND_LINES = {"9118000000001": "aquaspin", "9118000000002": "arcticair"}   # +91 1800 000 0001 / +91 1800 000 0002


def _now() -> str:
    return datetime.now().isoformat()


def _emit(brand: str, phone: str, sender: str, text: str, kind: str = "text", buttons: list | None = None, meta: dict | None = None) -> dict:
    msg = {"sender": sender, "kind": kind, "text": text, "created_at": _now()}
    if buttons:
        msg["buttons"] = buttons
    if meta:
        msg["meta"] = meta
    msg["cursor"] = get_store().put_chat_message(brand, phone, msg)
    return msg


def _index(brand: str, phone: str, name: str, last: str, mode: str, ticket_id: str = "", reason: str = "", unread: int = 0) -> None:
    get_store().put_chat_index(brand, phone, {"phone": phone, "customer_name": name, "last_text": last[:120], "mode": mode,
                                              "ticket_id": ticket_id, "reason": reason, "unread": unread, "updated_at": _now()})


def _first(name: str) -> str:
    return name.split()[0] if name else "there"


def _span(w: dict) -> str:
    end = datetime.strptime(w["ends"], "%Y-%m-%d")
    return f"active until {end:%d %b %Y}" if w["active"] else f"expired on {end:%d %b %Y}"


def announce_registration(reg: Registration) -> None:
    """Step 1 of the customer's story, for real: the moment an order file is ingested, each customer
    gets their registration message on that brand's WhatsApp line."""
    brand = brand_for(reg.product_id).lower()
    d = warranty_details(reg)
    comp, parts = d["coverage"]
    text = (f"Hi {_first(reg.customer_name)}! Your {reg.product_name} is registered with {BRAND_SLUGS[brand]}.\n"
            f"Serial {reg.serial_number}, bought {datetime.strptime(d['purchased'], '%Y-%m-%d'):%d %b %Y}.\n"
            f"{comp['label'].capitalize()} warranty ({comp['years']} years): {_span(comp)}.\n"
            f"Other parts (1 year): {_span(parts)}.\n"
            f"Message us here any time you need help or want to check your warranty.")
    _emit(brand, reg.customer_phone, "aftercare", text, meta={"kind": "registration", "serial": reg.serial_number})
    st = get_store()
    if not st.get_chat_state(brand, reg.customer_phone):
        st.put_chat_state(brand, reg.customer_phone, {"mode": "idle"})
    _index(brand, reg.customer_phone, reg.customer_name, "Registration confirmed", "idle")


def _distinct_tokens(reg: Registration, regs: list[Registration]) -> set[str]:
    def toks(r):
        return set(re.findall(r"[a-z0-9]+", f"{r.product_name} {r.product_id} {r.serial_number}".lower())) - _GENERIC
    others = set().union(*(toks(o) for o in regs if o.serial_number != reg.serial_number)) if len(regs) > 1 else set()
    return toks(reg) - others


def _pick_product(regs: list[Registration], text: str) -> Registration | None:
    """The one product this is about: the only one they own, or the one whose model / serial / distinctive
    name they mention. Otherwise None, and we ask."""
    if len(regs) == 1:
        return regs[0]
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    hits = [r for r in regs if _distinct_tokens(r, regs) & words]
    return hits[0] if len(hits) == 1 else None


def _ask_product(brand: str, phone: str, name: str, regs: list[Registration], pending: str) -> list[dict]:
    buttons = [{"id": f"prod:{r.serial_number}", "title": r.product_name.replace(BRAND_SLUGS[brand] + " ", "")[:24]} for r in regs[:3]]
    get_store().put_chat_state(brand, phone, {"mode": "awaiting_product", "pending": pending})
    _index(brand, phone, name, "Which product?", "awaiting_product")
    return [_emit(brand, phone, "aftercare", f"Thanks {_first(name)}. Which product is this about?", kind="buttons", buttons=buttons)]


def _deliver(brand: str, phone: str, name: str, data: dict, conv_id: str | None) -> list[dict]:
    """Turn an agent result into WhatsApp messages and update the chat state."""
    st = get_store()
    meta = {**(data.get("meta") or {}), "status": data["status"], "ticket_id": data.get("ticket_id", "")}
    out = []
    status = data["status"]
    if status == "waiting":
        out.append(_emit(brand, phone, "aftercare", data["message"], meta=meta))
        m = data.get("meta") or {}
        if m.get("section_heading"):
            out.append(_emit(brand, phone, "system", f"{BRAND_SLUGS[brand]} manual · {m['section_heading']}", kind="note"))
        st.put_chat_state(brand, phone, {"mode": "bot", "conversation_id": conv_id})
        _index(brand, phone, name, data["message"], "bot")
    elif status in ("resolved", "answered"):
        out.append(_emit(brand, phone, "aftercare", data["message"], meta=meta))
        if status == "resolved":
            out.append(_emit(brand, phone, "system", "Resolved. No ticket needed.", kind="note"))
        st.put_chat_state(brand, phone, {"mode": "idle"})
        _index(brand, phone, name, data["message"], "idle")
    else:  # escalated
        esc = (data.get("meta") or {}).get("escalation") or {}
        out.append(_emit(brand, phone, "aftercare", data["message"], meta=meta))
        out.append(_emit(brand, phone, "system", f"Ticket {data['ticket_id']} · {esc.get('label', 'Needs a person')}", kind="note"))
        st.put_chat_state(brand, phone, {"mode": "human", "ticket_id": data["ticket_id"], "acked": False})
        _index(brand, phone, name, data["message"], "human", data["ticket_id"], esc.get("label", ""), 0)
    return out


def _process(brand: str, phone: str, reg: Registration, text: str) -> list[dict]:
    data, status = core.start_conversation(phone, text, reg.product_id, serial=reg.serial_number)
    if status != 200:
        return [_emit(brand, phone, "aftercare", "Sorry, something went wrong on our side. Please try again.")]
    return _deliver(brand, phone, reg.customer_name, data, data.get("conversation_id"))


def _is_new_intent(text: str) -> bool:
    """Mid-conversation, these override "answering the last step": a safety word, a request for a person, a
    warranty question."""
    return bool(agent_mod._check_safety(text) or agent_mod._HUMAN.search(text) or agent_mod._is_coverage_question(text))


def handle_inbound(brand: str, phone: str, inbound: dict) -> list[dict]:
    """One customer message in, the replies out (also persisted to the chat log)."""
    st = get_store()
    text = (inbound.get("title") if inbound.get("type") == "button" else inbound.get("text", "")).strip()
    if not text:
        return []
    regs = [r for r in core.regs_for_phone(phone) if brand_for(r.product_id).lower() == brand]
    _emit(brand, phone, "customer", text)
    if not regs:
        return [_emit(brand, phone, "aftercare", f"I can't find a purchase registered to this number with {BRAND_SLUGS[brand]}. "
                                                 "If you bought recently, the store's order file may not have reached us yet.")]
    name = regs[0].customer_name
    state = st.get_chat_state(brand, phone) or {"mode": "idle"}
    mode = state.get("mode", "idle")

    if mode == "human":
        ticket = st.get_ticket(state.get("ticket_id", ""))
        if ticket and ticket.get("status") != "resolved":
            out = []
            if not state.get("acked"):
                out.append(_emit(brand, phone, "aftercare", "Your message has been added to your ticket. A person will reply here.", kind="note"))
                st.put_chat_state(brand, phone, {**state, "acked": True})
            idx = next((i for i in st.chat_index(brand) if i["phone"] == phone), {})
            _index(brand, phone, name, text, "human", state["ticket_id"], idx.get("reason", ""), int(idx.get("unread", 0)) + 1)
            return out
        mode, state = "idle", {"mode": "idle"}
        st.put_chat_state(brand, phone, state)

    if mode == "awaiting_product":
        chosen = None
        if inbound.get("type") == "button" and str(inbound.get("id", "")).startswith("prod:"):
            chosen = next((r for r in regs if r.serial_number == inbound["id"][5:]), None)
        chosen = chosen or _pick_product(regs, text)
        if chosen:
            return _process(brand, phone, chosen, state.get("pending", text))
        return _ask_product(brand, phone, name, regs, state.get("pending", text))

    if mode == "bot" and not _is_new_intent(text):
        data, status = core.respond_conversation(state["conversation_id"], text)
        if status == 200:
            return _deliver(brand, phone, name, data, state["conversation_id"])
        st.put_chat_state(brand, phone, {"mode": "idle"})

    # idle (or an interrupted conversation): a fresh message
    if text.lower().strip(" .!") == "report a problem":
        return [_emit(brand, phone, "aftercare", "Sure. Tell me what's happening, in your own words.")]
    if GREETING.match(text):
        names = ", ".join(r.product_name for r in regs)
        st.put_chat_state(brand, phone, {"mode": "idle"})
        _index(brand, phone, name, "Greeting", "idle")
        return [_emit(brand, phone, "aftercare",
                      f"Hi {_first(name)}! I'm {BRAND_SLUGS[brand]}'s support assistant. I can see your {names}. "
                      "Ask me about your warranty, or tell me what's going wrong.",
                      kind="buttons", buttons=[{"id": "cmd:warranty", "title": "Check my warranty"}, {"id": "cmd:problem", "title": "Report a problem"}])]
    reg = _pick_product(regs, text)
    if reg is None:
        return _ask_product(brand, phone, name, regs, text)
    return _process(brand, phone, reg, text)


def parse_webhook(payload: dict) -> list[tuple[str, str, dict]]:
    """Meta's WhatsApp Cloud API webhook shape -> [(brand, customer phone, inbound)]."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            line = re.sub(r"\D", "", value.get("metadata", {}).get("display_phone_number", ""))
            brand = BRAND_LINES.get(line)
            if not brand:
                continue
            for m in value.get("messages", []):
                phone = "+" + re.sub(r"\D", "", str(m.get("from", "")))
                if m.get("type") == "text":
                    out.append((brand, phone, {"type": "text", "text": str((m.get("text") or {}).get("body", ""))[:1000]}))
                elif m.get("type") == "interactive":
                    br = (m.get("interactive") or {}).get("button_reply", {})
                    out.append((brand, phone, {"type": "button", "id": br.get("id", ""), "title": br.get("title", "")}))
    return out


def staff_reply(ticket: dict, text: str, staff_name: str) -> dict:
    """A person answers from the brand's inbox: just another message in the same chat log."""
    brand = brand_for(ticket["product_id"]).lower()
    phone = ticket["customer_phone"]
    st = get_store()
    msg = _emit(brand, phone, "human", text, meta={"staff": staff_name, "ticket_id": ticket["ticket_id"]})
    state = st.get_chat_state(brand, phone) or {}
    st.put_chat_state(brand, phone, {**state, "mode": "human", "ticket_id": ticket["ticket_id"], "acked": True})
    _index(brand, phone, ticket["customer_name"], text, "human", ticket["ticket_id"], ticket.get("reason_code", ""), 0)
    return msg


def ticket_resolved(ticket: dict, staff_name: str) -> None:
    brand = brand_for(ticket["product_id"]).lower()
    phone = ticket["customer_phone"]
    _emit(brand, phone, "system", f"Ticket {ticket['ticket_id']} was marked resolved by {staff_name}.", kind="note")
    get_store().put_chat_state(brand, phone, {"mode": "idle"})
    _index(brand, phone, ticket["customer_name"], "Ticket resolved", "idle", ticket["ticket_id"])
