"""Route-agnostic core logic, shared by two adapters: the Flask dev
server (app.py, what the live demo runs) and the SAM Local Lambda
handlers (../lambda_handlers.py, proof the same logic is serverless-
ready). One real implementation -- an adapter translates its own
request/response shape into calls here and back, nothing
product-specific lives in either adapter.

Conversation state is saved to data/conversations/<id>.json, same
pattern as Ticket's file storage -- not an in-memory dict. That started
as one, until running the two adapters side by side (Phase 7.5) showed
why it can't be: start_conversation() and respond_conversation() are
two *separate* Lambda functions under SAM Local, each its own process
with its own memory, so an in-memory dict never actually shared state
between them -- not a cold-start edge case, every single call. Flask
gets the same fix for free, and gains "survives a dev-server restart"
as a side effect.

--- Audit fixes applied here (see IMPLEMENTATION.md Phase audit pass) ---

1. list_customers() now accepts brand filter -- the demo is brand-scoped,
   so the picker must show only that brand's customers, not everyone.

2. lookup() now accepts brand -- scopes returned products to that brand
   only. In a real deployment, the brand is known from which WhatsApp
   Business number the message arrived on; in the demo, it's the brand
   the user chose at entry. This removes the regs[0].brand guessing.

3. start_conversation() now requires product_id -- the customer picks
   which product they want support for (or the QR deep-link encodes it).
   Using regs[0] was always wrong: if a customer has two products and
   asks about the second one, it would service the first. Silent and
   wrong.

4. dashboard_data() now includes the full registrations list -- needed
   for the QR code section (each product gets a QR linking back to the
   WhatsApp support line with the serial pre-filled).
"""

import json
import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.authz import cedar_authz, session
from src.authz.cedar_authz import CedarUnavailable
from src.layer1.catalog import BRAND_SLUGS, brand_for
from src.layer1.registration import Registration, load_registrations, lookup_by_phone
from src.layer2 import agent as agent_mod
from src.layer3b import case_index
from src.storage import get_store
from src.layer3b.tickets import Ticket

_agent = None  # built lazily, once, on first use -- avoids paying Ollama startup cost at import time
def get_agent():
    global _agent
    if _agent is None:
        _agent = agent_mod._build_agent()
    return _agent


def _save_conversation(conv_id: str, conv: agent_mod.Conversation) -> None:
    get_store().put_conversation(conv_id, asdict(conv))


def _load_conversation(conv_id: str) -> agent_mod.Conversation | None:
    data = get_store().get_conversation(conv_id)
    if data is None:
        return None
    return agent_mod.Conversation(
        registration=Registration(**data["registration"]),
        complaint=data["complaint"],
        source=data["source"],
        section_heading=data["section_heading"],
        section_body=data["section_body"],
        available_steps=data["available_steps"],
        turns=[agent_mod.Turn(**t) for t in data["turns"]],
        safety_flag=data["safety_flag"],
        resolved=data["resolved"],
        ticket=Ticket(**data["ticket"]) if data["ticket"] else None,
        retrieval_method=data.get("retrieval_method", ""),
        escalation_code=data.get("escalation_code", ""),
        escalation_detail=data.get("escalation_detail", ""),
        created_at=data.get("created_at", ""),
    )


HISTORY_SEED = Path(__file__).resolve().parent.parent.parent / "fixtures" / "history_seed.json"


def _history(serial: str = "") -> tuple[list[agent_mod.PriorCase], str]:
    """Earlier cases the agent can recognise a recurring problem from. Returns (cases, engine).

    OpenSearch answers it as a query (serial + time window, seeded with the history a
    brand's ticketing system would already hold). If it is unreachable, the storage
    backend answers the same question from its own access pattern (DynamoDB: a GSI query
    on the serial; files: a scan), plus the seed file. Seed ages are relative, so the
    demo scenario doesn't drift out of the window."""
    try:
        found = case_index.prior_cases(serial, agent_mod.RECURRENCE_DAYS)
        return [agent_mod.PriorCase(serial_number=d["serial_number"], section_heading=d["section_heading"],
                                    when=datetime.fromisoformat(d["created_at"]).replace(tzinfo=None),
                                    outcome=d["outcome"]) for d in found], "opensearch"
    except Exception:
        pass
    cutoff = (datetime.now() - timedelta(days=agent_mod.RECURRENCE_DAYS)).isoformat()
    cases = [
        agent_mod.PriorCase(serial_number=c["serial_number"], section_heading=c["section_heading"],
                            when=datetime.fromisoformat(c["created_at"]), outcome=c["outcome"])
        for c in get_store().cases_for_serial(serial, cutoff) if c.get("source") == "manual"
    ]
    if HISTORY_SEED.exists():
        for e in json.loads(HISTORY_SEED.read_text()):
            if e["serial_number"] == serial:
                cases.append(agent_mod.PriorCase(
                    serial_number=serial, section_heading=e["section_heading"],
                    when=datetime.now() - timedelta(days=e["days_ago"]), outcome=e["outcome"]))
    return cases, get_store().name


def reset_demo_data() -> dict:
    """Clear conversations and tickets so a demo run starts clean (otherwise the first run
    makes the second look like a recurring issue)."""
    n = get_store().clear()
    try:
        case_index.reset()
    except Exception:
        pass
    return {"cleared": n}


def _record(conv_id: str, conv: agent_mod.Conversation) -> None:
    """A finished conversation becomes a *case*: written to the storage backend (recurrence
    fallback, insights fallback) and indexed in OpenSearch (recurrence and insights as
    queries). Best effort: the conversation itself is already saved, so a failure here
    never breaks a reply."""
    if not (conv.resolved or conv.ticket):
        return
    reg = conv.registration
    brand = brand_for(reg.product_id).lower()
    try:
        get_store().put_case(brand, {
            "conversation_id": conv_id, "brand": brand, "serial_number": reg.serial_number, "product_id": reg.product_id,
            "section_heading": conv.section_heading, "source": "safety" if conv.safety_flag else conv.source,
            "outcome": "resolved" if conv.resolved else "escalated", "reason_code": conv.escalation_code,
            "created_at": conv.created_at,
        })
    except Exception:
        pass
    try:
        case_index.record(conv_id, conv)
    except Exception:
        pass


def list_customers(brand: str = "") -> list[dict]:
    """For the demo's 'simulate as' picker only. A real WhatsApp
    integration never needs this -- the incoming message already
    carries the sender's number, per WhatsApp's own webhook payload.

    brand: if provided (e.g. 'arcticair'), return only customers who
    have at least one product from that brand. The demo is brand-scoped --
    ArcticAir's support line sees ArcticAir customers, not AquaSpin's.
    Mixing them in one picker was a design flaw: the two brands are
    independent, each with their own WhatsApp Business number."""
    seen: dict[str, str] = {}
    for r in load_registrations():
        # Filter to brand if requested -- brand is the slug (lowercase)
        if brand and brand_for(r.product_id).lower() != brand.lower():
            continue
        seen.setdefault(r.customer_phone, r.customer_name)
    return [{"phone": phone, "name": name} for phone, name in seen.items()]


def lookup(phone: str, brand: str = "") -> dict:
    """Look up a customer by phone, scoped to a brand.

    brand: the brand whose WhatsApp line the customer is messaging on.
    A customer with both an AquaSpin and ArcticAir product messaging
    AquaSpin's number should only see their AquaSpin products here --
    the other brand is irrelevant to this conversation.

    In a real deployment, brand comes from which number the message
    arrived on -- it's never user-supplied or guessed. In the demo,
    it comes from the brand the user picked at the entry screen."""
    all_regs = lookup_by_phone(phone, load_registrations())
    if not all_regs:
        return {"found": False}

    # Scope to this brand's products only
    if brand:
        regs = [r for r in all_regs if brand_for(r.product_id).lower() == brand.lower()]
    else:
        regs = all_regs

    if not regs:
        return {"found": False}

    # brand is the same for all filtered registrations -- safe to read from the first
    derived_brand = brand_for(regs[0].product_id)
    return {
        "found": True,
        "customer_name": regs[0].customer_name,
        "brand": derived_brand,
        "brand_slug": derived_brand.lower(),
        "products": [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "serial_number": r.serial_number,
                "purchase_date": r.purchase_date,
                "warranty_component_status": r.warranty_component_status,
                "warranty_parts_status": r.warranty_parts_status,
            }
            for r in regs
        ],
    }


def start_conversation(phone: str, complaint: str, product_id: str) -> tuple[dict, int]:
    """Start a support conversation for a specific product.

    product_id is required -- the customer has already selected which
    product they need help with (either via the product picker UI or
    via a QR deep-link encoding the serial). Using regs[0] was wrong:
    a customer with two products would always get support for the first
    registered one, regardless of which machine they asked about."""
    all_regs = lookup_by_phone(phone, load_registrations())
    # Find the exact registration the customer selected
    matching = [r for r in all_regs if r.product_id == product_id]
    if not matching:
        return {"error": f"No registration found for product {product_id} on this number."}, 404

    reg = matching[0]  # product_id is a precise match -- all registrations for the same
                       # product_id on this phone are the same product type; take first.
                       # A real system would match on serial_number too for absolute precision.

    conv = agent_mod.start(reg, complaint, agent=get_agent(), history=_history(reg.serial_number)[0])
    conv_id = str(uuid.uuid4())
    _save_conversation(conv_id, conv)
    _record(conv_id, conv)
    return {"conversation_id": conv_id, **_conversation_state(conv)}, 200


def respond_conversation(conversation_id: str, reply: str) -> tuple[dict, int]:
    conv = _load_conversation(conversation_id)
    if conv is None:
        return {"error": "Unknown conversation."}, 404

    conv = agent_mod.respond(conv, reply, agent=get_agent())
    _save_conversation(conversation_id, conv)
    _record(conversation_id, conv)
    return _conversation_state(conv), 200


def _insights(brand: str) -> dict:
    try:
        out = case_index.insights(brand)
    except Exception:
        out = _insights_from_store(brand)
    for r in out["by_reason"]:
        r["label"] = agent_mod.ESCALATION_LABELS.get(r["code"], r["code"])
    return out


def _insights_from_store(brand: str) -> dict:
    """Same shape as case_index.insights(), computed by hand when OpenSearch is down."""
    resolved = escalated = 0
    reasons: dict[str, int] = {}
    sections: dict[str, list[int]] = {}
    for c in get_store().cases_for_brand(brand):
        done = c["outcome"] == "resolved"
        resolved += done
        escalated += not done
        if not done and c.get("reason_code"):
            reasons[c["reason_code"]] = reasons.get(c["reason_code"], 0) + 1
        if c.get("section_heading"):
            row = sections.setdefault(c["section_heading"], [0, 0])
            row[0] += 1
            row[1] += (not done)
    return {
        "engine": get_store().name, "resolved": resolved, "escalated": escalated,
        "by_reason": [{"code": k, "count": v} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])],
        "top_sections": [{"heading": k, "count": v[0], "escalated": v[1]}
                         for k, v in sorted(sections.items(), key=lambda kv: -kv[1][0])[:5]],
    }


def mask_phone(phone: str) -> str:
    """+919876543210 -> '+91 98765 \u00b7\u00b7\u00b7\u00b7\u00b7'"""
    digits = phone.lstrip("+")
    if len(digits) == 12 and digits.startswith("91"):
        return f"+91 {digits[2:7]} \u00b7\u00b7\u00b7\u00b7\u00b7"
    return phone[:4] + " \u00b7\u00b7\u00b7\u00b7\u00b7"


def _cedar_principal(p: session.Principal) -> dict:
    return {"id": p.username, "brand": p.brand, "role": p.role}


def login(username: str, passcode: str) -> tuple[dict, int]:
    p = session.authenticate(username.strip(), passcode)
    if p is None:
        return {"error": "Wrong username or passcode."}, 401
    return {"token": session.issue(p), "principal": asdict(p)}, 200


def me(token: str | None) -> tuple[dict, int]:
    p = session.verify(token)
    return ({"principal": asdict(p)}, 200) if p else ({"error": "Not signed in."}, 401)


def _deny_message(p: session.Principal, what: str, d: cedar_authz.Decision) -> str:
    rule = ", ".join(d.policies) or "no policy permits it"
    return f"{p.name} ({p.brand} {p.role}) may not {what}. Cedar decided by: {rule}."


def dashboard_data(brand: str, token: str | None, q: str = "") -> tuple[dict, int]:
    """Brand-scoped, Cedar-authorized. The principal comes from the signed session
    cookie (server-side), the resource from the URL; Cedar -- not an if-statement --
    decides whether they match, and says which policy decided."""
    brand = brand.strip().lower()
    principal = session.verify(token)
    if principal is None:
        return {"error": "Not signed in."}, 401

    try:
        decision = cedar_authz.can_view_dashboard(_cedar_principal(principal), brand)
    except CedarUnavailable as exc:
        return {"error": f"Authorization check unavailable: {exc}"}, 503

    if not decision.allowed:
        return {"error": _deny_message(principal, f"view {brand}'s dashboard", decision), "decision": {"allowed": False, "policies": decision.policies}}, 403

    registrations = [r for r in load_registrations() if brand_for(r.product_id).lower() == brand]
    tickets = [Ticket(**d) for d in get_store().tickets(brand)]

    if q.strip():
        try:
            hits = set(case_index.search_tickets(brand, q.strip()))
            tickets = [t for t in tickets if t.ticket_id in hits]
        except Exception:
            ql = q.strip().lower()
            tickets = [t for t in tickets if ql in f"{t.customer_name} {t.product_name} {t.issue_summary}".lower()]

    # Phones are masked unless Cedar says this principal may see this ticket's number in full.
    phone_shown = {}
    for t in tickets:
        try:
            full = cedar_authz.authorize(_cedar_principal(principal), "viewPhoneUnmasked", "Ticket", t.ticket_id,
                                         {"brand": brand, "safety": bool(t.safety_flag)}).allowed
        except CedarUnavailable:
            full = False
        phone_shown[t.ticket_id] = (t.customer_phone if full else mask_phone(t.customer_phone), full)

    warranty_counts = {"active": 0, "expired": 0}
    for r in registrations:
        warranty_counts["active" if r.warranty_component_status == "active" else "expired"] += 1
        warranty_counts["active" if r.warranty_parts_status == "active" else "expired"] += 1

    product_feedback: dict[str, int] = {}
    for t in tickets:
        product_feedback[t.product_name] = product_feedback.get(t.product_name, 0) + 1

    # QR whatsapp deep-link: in production this would be the brand's real
    # WhatsApp Business number. For the demo, we use a placeholder that
    # encodes the intent: customer scans, WhatsApp opens pre-addressed
    # to that brand's support line with the serial pre-filled.
    brand_display = BRAND_SLUGS.get(brand, brand)
    whatsapp_demo_base = f"https://wa.me/message/{brand}"  # placeholder -- real number goes here

    return {
        "brand": brand,
        "authz": {"principal": asdict(principal), "decision": {"allowed": True, "policies": decision.policies}},
        "insights": _insights(brand),
        "tickets": [
            {
                "ticket_id": t.ticket_id,
                "customer_name": t.customer_name,
                "product_name": t.product_name,
                "issue_summary": t.issue_summary,
                "attempts_tried": t.attempts_tried,
                "safety_flag": t.safety_flag,
                "customer_phone": phone_shown[t.ticket_id][0],
                "phone_unmasked": phone_shown[t.ticket_id][1],
                "reason_code": t.reason_code,
                "reason_label": agent_mod.ESCALATION_LABELS.get(t.reason_code, ""),
                "status": t.status,
                "created_at": t.created_at,
            }
            for t in tickets
        ],
        "warranty_counts": warranty_counts,
        "product_feedback": [{"product_name": k, "count": v} for k, v in sorted(product_feedback.items(), key=lambda kv: -kv[1])],
        "registered_count": len(registrations),
        # Full registration list for the QR code section -- brand staff
        # can see each registered product and its QR code link.
        "registrations": [
            {
                "customer_name": r.customer_name,
                "product_id": r.product_id,
                "product_name": r.product_name,
                "serial_number": r.serial_number,
                "purchase_date": r.purchase_date,
                "retailer": r.retailer,
                "warranty_component_status": r.warranty_component_status,
                "warranty_parts_status": r.warranty_parts_status,
                # QR encodes a WhatsApp deep link so the customer can scan
                # and start a support conversation with context pre-loaded.
                "qr_content": f"https://wa.me/message/{brand}?serial={r.serial_number}",
            }
            for r in registrations
        ],
    }, 200


def health() -> dict:
    """Live probes, no cached answers: each component reports what it actually
    did just now. The landing page's "under the hood" chips and the demo's
    runtime pill read this, so a stopped container shows up as stopped."""
    import hashlib
    import time
    import urllib.request

    from src.layer1 import opensearch_retrieval as osr

    def probe(fn):
        t0 = time.perf_counter()
        try:
            detail = fn()
            return {"ok": True, "ms": round((time.perf_counter() - t0) * 1000), **detail}
        except Exception as exc:  # any failure is the answer here
            return {"ok": False, "ms": round((time.perf_counter() - t0) * 1000), "error": str(exc)[:120]}

    def ollama():
        with urllib.request.urlopen(f"{agent_mod.OLLAMA_HOST}/api/tags", timeout=2) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return {"models": models}

    def opensearch():
        c = osr._get_client()
        info = c.info()
        docs = c.count(index=osr.INDEX_NAME)["count"] if c.indices.exists(index=osr.INDEX_NAME) else 0
        return {"version": info["version"]["number"], "index": osr.INDEX_NAME, "documents": docs}

    def cedar():
        if not cedar_authz.CEDAR_BIN.exists():
            raise RuntimeError("Cedar CLI missing")
        ok, msg = cedar_authz.validate()
        if not ok:
            raise RuntimeError("policies fail cedar validate")
        return {"policy_sha": hashlib.sha256(cedar_authz.POLICY_PATH.read_bytes()).hexdigest()[:8], "validated": True}

    return {
        "runtime": "lambda" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "flask",
        "storage": get_store().name,
        "components": {"ollama": probe(ollama), "opensearch": probe(opensearch), "cedar": probe(cedar)},
    }


TICKET_STATUSES = ("new", "in_progress", "resolved")


def update_ticket_status(ticket_id: str, status: str, token: str | None) -> tuple[dict, int]:
    principal = session.verify(token)
    if principal is None:
        return {"error": "Not signed in."}, 401
    if status not in TICKET_STATUSES:
        return {"error": f"status must be one of {TICKET_STATUSES}"}, 400
    row = get_store().get_ticket(ticket_id)
    if row is None:
        return {"error": "Unknown ticket."}, 404
    ticket = Ticket(**row)
    try:
        d = cedar_authz.authorize(_cedar_principal(principal), "updateTicketStatus", "Ticket", ticket_id,
                                  {"brand": brand_for(ticket.product_id).lower(), "safety": bool(ticket.safety_flag)})
    except CedarUnavailable as exc:
        return {"error": f"Authorization check unavailable: {exc}"}, 503
    if not d.allowed:
        return {"error": _deny_message(principal, f"change ticket {ticket_id}", d), "decision": {"allowed": False, "policies": d.policies}}, 403
    ticket.status = status
    ticket.save()
    return {"ticket_id": ticket_id, "status": status, "decision": {"allowed": True, "policies": d.policies}}, 200


def _clean(message: str) -> str:
    """The model occasionally wraps its answer in quote marks despite
    being asked not to add anything extra -- strip them rather than
    show the customer a stray quoted string."""
    return message.strip().strip('"').strip()


def _escalation_message(conv: agent_mod.Conversation) -> str:
    """What the customer is told, by *why* a person is stepping in."""
    tid = conv.ticket.ticket_id
    code = conv.escalation_code
    if code == "safety":
        stop = conv.section_body or "Please stop using the product."
        return (
            f"{stop}\n\nThis is a safety issue, so I won't try to troubleshoot it over chat. "
            f"I've raised ticket {tid} for an emergency technician visit -- free of charge whatever your warranty status."
        )
    if code == "recurring":
        when = conv.escalation_detail.split(" -- handled ", 1)[-1].split(" (")[0]
        return (
            f"This looks like the same problem we handled on {when}. "
            f"Repeating the same fix won't help, so I've passed it to our service team as ticket {tid}, "
            f"with the earlier case attached. You won't have to explain it again."
        )
    if code == "unmatched":
        return (
            f"I couldn't find this in your product manual, and I won't guess at it. "
            f"I've handed it to our service team as ticket {tid} with your description as written."
        )
    if code == "attempts_exhausted":
        return (
            f"Sorry those two steps didn't fix it. I've handed this to our service team as ticket {tid}, "
            f"including what we already tried, so you won't be asked to repeat it."
        )
    if code == "no_more_steps":
        return (
            f"That was the last self-service step in the manual. I've handed this to our service team "
            f"as ticket {tid}, including what we tried."
        )
    return f"This one needs a person. I've raised ticket {tid} for our service team, who'll follow up within 5 business days."


def _conversation_state(conv: agent_mod.Conversation) -> dict:
    """What the frontend needs to render the next thing to show. `meta` is
    the 'what Aftercare did' trace the demo displays -- all of it read from
    the conversation, none of it invented for display."""
    reg = conv.registration
    meta = {
        "source": conv.source,
        "section_heading": conv.section_heading,
        "retrieval_method": conv.retrieval_method,
        "attempt": len(conv.turns),
        "max_attempts": agent_mod.MAX_ATTEMPTS,
        "escalation": None,
        "warranty": {"component": reg.warranty_component, "component_status": reg.warranty_component_status,
                     "parts_status": reg.warranty_parts_status},
    }
    if conv.resolved:
        return {"status": "resolved", "message": "Glad that fixed it! Let us know if anything else comes up.", "meta": meta}
    if conv.ticket is not None:
        meta["escalation"] = {
            "code": conv.escalation_code,
            "label": agent_mod.ESCALATION_LABELS.get(conv.escalation_code, ""),
            "detail": conv.escalation_detail,
        }
        return {
            "status": "escalated",
            "message": _escalation_message(conv),
            "ticket_id": conv.ticket.ticket_id,
            "ticket": {
                "customer_name": conv.ticket.customer_name,
                "product_name": conv.ticket.product_name,
                "serial_number": conv.ticket.serial_number,
                "issue_summary": conv.ticket.issue_summary,
                "attempts_tried": [_clean(a) for a in conv.ticket.attempts_tried],
                "safety_flag": conv.ticket.safety_flag,
            },
            "meta": meta,
        }
    return {"status": "waiting", "message": _clean(conv.turns[-1].step), "meta": meta}
