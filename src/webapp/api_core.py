"""Business logic behind every route (src/lambda_app.py is the only adapter).

Route-agnostic and framework-free: lambda_app.py translates an API Gateway event into calls here and back; pages.py
renders the HTML. State lives behind src/storage (DynamoDB); manual search, recurrence and analytics are OpenSearch
(src/records/case_index.py, src/domain/opensearch_retrieval.py); who-may-do-what is Cedar (src/authz). Nothing here
falls back to anything: a missing service raises DependencyUnavailable, which the Lambda turns into a 503.

The WhatsApp channel (greeting, product picker, hand-over, replies) is src/channel/bot.py, which calls back into
start_conversation / respond_conversation here so there is one implementation of "run the agent".
"""

import json
import os
import sys
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.authz import cedar_authz, session
from src.authz.cedar_authz import CedarUnavailable
from src.domain.catalog import BRAND_SLUGS, brand_for
from src.domain.registration import Registration, registration_from_row
from src.agent import agent as agent_mod
from src.records import case_index
from src.storage import get_store
from src.webapp import observability as obs
from src.records.tickets import Ticket

_agent = None  # built lazily, once, on first use -- avoids paying Ollama startup cost at import time
def get_agent():
    global _agent
    if _agent is None:
        _agent = agent_mod._build_agent()
    return _agent


def _drain_model_ms() -> list[int]:
    """Milliseconds of each model call made for this request (Strands hooks); [] for test doubles."""
    drain = getattr(get_agent(), "drain_model_ms", None)
    return drain() if drain else []


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


def _history(serial: str) -> list[agent_mod.PriorCase]:
    """Earlier cases for this serial inside the recurrence window, from an OpenSearch query
    (serial + source + `range now-90d`). Seed history (what a brand's ticketing system would already
    hold) is indexed by the bootstrap. Raises DependencyUnavailable if OpenSearch is down."""
    return [
        agent_mod.PriorCase(serial_number=d["serial_number"], section_heading=d["section_heading"],
                            when=datetime.fromisoformat(d["created_at"]).replace(tzinfo=None), outcome=d["outcome"])
        for d in case_index.prior_cases(serial, agent_mod.RECURRENCE_DAYS)
    ]


def reset_demo_data() -> dict:
    """Clear conversations and tickets so a demo run starts clean (otherwise the first run
    makes the second look like a recurring issue)."""
    n = get_store().clear()
    case_index.reset()
    return {"cleared": n}


def _record(conv_id: str, conv: agent_mod.Conversation) -> None:
    """A finished conversation becomes a *case*: written to DynamoDB (the source of truth) and
    indexed in OpenSearch (recurrence and insights are queries over it). Failures are raised, not hidden."""
    if not (conv.resolved or conv.ticket or conv.answered):
        return
    reg = conv.registration
    brand = brand_for(reg.product_id).lower()
    get_store().put_case(brand, {
        "conversation_id": conv_id, "brand": brand, "serial_number": reg.serial_number, "product_id": reg.product_id,
        "section_heading": conv.section_heading, "source": "safety" if conv.safety_flag else conv.source,
        "outcome": "resolved" if conv.resolved else "answered" if conv.answered else "escalated",
        "reason_code": conv.escalation_code, "created_at": conv.created_at,
    })
    case_index.record(conv_id, conv)


def regs_for_phone(phone: str) -> list[Registration]:
    """Everything this phone number has bought, from the registry (DynamoDB, GSI on the phone)."""
    return [registration_from_row(r) for r in get_store().registrations_for_phone(phone)]


def regs_for_brand(brand: str) -> list[Registration]:
    return [registration_from_row(r) for r in get_store().registrations(brand)]


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
    for r in [x for b in ((brand,) if brand else BRAND_SLUGS) for x in regs_for_brand(b.lower())]:
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
    all_regs = regs_for_phone(phone)
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


def start_conversation(phone: str, complaint: str, product_id: str, idempotency_key: str | None = None, serial: str | None = None) -> tuple[dict, int]:
    """Idempotent when the caller supplies a key (Idempotency-Key header) and the DynamoDB
    store is active: a retried request returns the same conversation instead of creating a
    second conversation and a second ticket."""
    if idempotency_key and get_store().name == "dynamodb":
        from src.webapp.idempotency import once
        out = once(payload={"key": idempotency_key, "phone": phone, "complaint": complaint, "product_id": product_id})
        return out["data"], out["status"]
    return _start_conversation(phone, complaint, product_id, serial)


def _start_conversation(phone: str, complaint: str, product_id: str, serial: str | None = None) -> tuple[dict, int]:
    """Start a support conversation for a specific product.

    product_id is required -- the customer has already selected which
    product they need help with (either via the product picker UI or
    via a QR deep-link encoding the serial). Using regs[0] was wrong:
    a customer with two products would always get support for the first
    registered one, regardless of which machine they asked about."""
    all_regs = regs_for_phone(phone)
    # Find the exact registration the customer selected (by serial when we have it, else by product id)
    matching = [r for r in all_regs if (r.serial_number == serial if serial else r.product_id == product_id)]
    if not matching:
        return {"error": f"No registration found for product {product_id} on this number."}, 404

    reg = matching[0]  # product_id is a precise match -- all registrations for the same
                       # product_id on this phone are the same product type; take first.
                       # A real system would match on serial_number too for absolute precision.

    t0 = time.perf_counter()
    history = _history(reg.serial_number)
    conv = agent_mod.start(reg, complaint, agent=get_agent(), history=history)
    agent_ms = round((time.perf_counter() - t0) * 1000)
    conv_id = str(uuid.uuid4())
    _save_conversation(conv_id, conv)
    _record(conv_id, conv)
    state = _conversation_state(conv)
    obs.conversation_outcome(state, brand_for(reg.product_id).lower(), agent_ms)
    state["meta"]["model_ms"] = _drain_model_ms()
    state["meta"]["history_engine"] = "opensearch"
    state["meta"]["storage"] = get_store().name
    return {"conversation_id": conv_id, **state}, 200


def respond_conversation(conversation_id: str, reply: str) -> tuple[dict, int]:
    conv = _load_conversation(conversation_id)
    if conv is None:
        return {"error": "Unknown conversation."}, 404

    t0 = time.perf_counter()
    conv = agent_mod.respond(conv, reply, agent=get_agent())
    agent_ms = round((time.perf_counter() - t0) * 1000)
    _save_conversation(conversation_id, conv)
    _record(conversation_id, conv)
    state = _conversation_state(conv)
    obs.conversation_outcome(state, brand_for(conv.registration.product_id).lower(), agent_ms)
    state["meta"]["model_ms"] = _drain_model_ms()
    state["meta"]["storage"] = get_store().name
    return state, 200


def _insights(brand: str) -> dict:
    out = case_index.insights(brand)
    for r in out["by_reason"]:
        r["label"] = agent_mod.ESCALATION_LABELS.get(r["code"], r["code"])
    return out


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
        obs.logger.warning("authz_denied", action="viewDashboard", principal_brand=principal.brand, role=principal.role,
                           resource_brand=brand, policies=decision.policies)
        obs.metric("AuthzDenied", Action="viewDashboard")
        return {"error": _deny_message(principal, f"view {brand}'s dashboard", decision), "decision": {"allowed": False, "policies": decision.policies}}, 403

    registrations = regs_for_brand(brand)
    tickets = [Ticket(**d) for d in get_store().tickets(brand)]

    if q.strip():
        hits = set(case_index.search_tickets(brand, q.strip()))
        tickets = [t for t in tickets if t.ticket_id in hits]

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
                "warranty_component": r.warranty_component,
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
    """Live probes, no cached answers: each backing service reports what it actually did just now.
    The landing page's chips and the demo's runtime pill read this."""
    import hashlib
    import urllib.request

    from src.domain import opensearch_retrieval as osr

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
        return {"version": info["version"]["number"], "index": osr.INDEX_NAME, "documents": c.count(index=osr.INDEX_NAME)["count"]}

    def cedar():
        ok, _ = cedar_authz.validate()
        if not ok:
            raise RuntimeError("policies fail cedar validate")
        return {"policy_sha": hashlib.sha256(cedar_authz.POLICY_PATH.read_bytes()).hexdigest()[:8], "validated": True}

    def dynamodb():
        store = get_store()
        return {"backend": store.name, "table": getattr(store, "_table").table_name, "items": getattr(store, "_table").item_count}

    return {
        "runtime": "lambda" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "local",
        "storage": get_store().name,
        "components": {"ollama": probe(ollama), "opensearch": probe(opensearch), "cedar": probe(cedar), "dynamodb": probe(dynamodb)},
    }


REQUIRED_COLUMNS = ("customer_name", "customer_phone", "product_id", "product_name", "serial_number", "purchase_date", "retailer", "purchase_price")
MAX_CSV_BYTES = 200_000


def _parse_orders(csv_text: str) -> tuple[list[dict], list[dict], int] | tuple[dict, int]:
    """Read an order file row by row. Returns (accepted rows, issues, total rows), or an (error, status)
    pair if the file itself is unusable. Each accepted row is filed under the brand that owns its product code."""
    import csv
    import io
    import re

    if len(csv_text.encode()) > MAX_CSV_BYTES:
        return {"error": f"File too large for the demo (limit {MAX_CSV_BYTES // 1000} KB)."}, 413
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        return {"error": f"Missing column(s): {', '.join(missing)}", "expected": list(REQUIRED_COLUMNS)}, 422

    issues: list[dict] = []
    seen: dict[str, int] = {}
    accepted: list[dict] = []
    total = 0
    for line, row in enumerate(reader, start=2):
        total += 1
        if total > 2000:
            issues.append({"line": line, "problem": "Stopped at 2,000 rows (demo limit)."})
            break
        row = {k: (v or "").strip() for k, v in row.items() if k in REQUIRED_COLUMNS}
        problems = []
        try:
            brand_for(row["product_id"])
        except ValueError:
            problems.append(f"Unknown product code \"{row['product_id']}\": no brand owns it")
        try:
            datetime.strptime(row["purchase_date"], "%Y-%m-%d")
        except ValueError:
            problems.append(f"Purchase date \"{row['purchase_date']}\" is not YYYY-MM-DD")
        if not re.fullmatch(r"\+\d{10,15}", row["customer_phone"]):
            problems.append("Phone is not in +<country code><number> form")
        if not row["serial_number"]:
            problems.append("Serial number is empty")
        elif row["serial_number"] in seen:
            problems.append(f"Serial {row['serial_number']} already appears on line {seen[row['serial_number']]}")
        else:
            seen[row["serial_number"]] = line
        if not row["purchase_price"].isdigit():
            problems.append("Purchase price is not a whole number")
        if problems:
            issues.extend({"line": line, "problem": p} for p in problems)
        else:
            accepted.append(row)
    return accepted, issues, total


def _orders_summary(accepted: list[dict], issues: list[dict], total: int) -> dict:
    by_brand: dict[str, dict] = {}
    for row in accepted:
        brand = brand_for(row["product_id"])
        e = by_brand.setdefault(brand, {"brand": brand, "slug": brand.lower(), "products": 0, "phones": set()})
        e["products"] += 1
        e["phones"].add(row["customer_phone"])
    return {
        "rows": total, "accepted": len(accepted), "rejected": total - len(accepted),
        "brands": [{"brand": e["brand"], "slug": e["slug"], "products": e["products"], "customers": len(e["phones"])}
                   for e in sorted(by_brand.values(), key=lambda e: e["brand"])],
        "issues": issues[:25],
    }


def ingest_preview(csv_text: str) -> tuple[dict, int]:
    """Check an order file without saving it: files each product under its brand and reports what it
    can't place (unknown codes, bad dates, malformed phones, duplicate serials) instead of guessing."""
    parsed = _parse_orders(csv_text)
    if len(parsed) == 2:
        return parsed
    return _orders_summary(*parsed), 200


def ingest_commit(csv_text: str, source: str = "upload") -> tuple[dict, int]:
    """Check the file, then register every accepted row (DynamoDB registry, keyed by brand and phone)
    and send each customer their registration message on that brand's WhatsApp line. Rejected rows are
    reported, not saved. In production the upload lands in S3 and an event triggers this."""
    parsed = _parse_orders(csv_text)
    if len(parsed) == 2:
        return parsed
    accepted, issues, total = parsed
    from src.channel import bot
    for row in accepted:
        get_store().put_registration({**row, "purchase_price": int(row["purchase_price"]), "source": source})
        bot.announce_registration(registration_from_row(row))
    out = _orders_summary(accepted, issues, total)
    out["registered"] = len(accepted)
    out["messages_sent"] = len(accepted)
    return out, 200


TICKET_STATUSES = ("new", "in_progress", "resolved")


def _ticket_access(token: str | None, ticket_id: str, action: str, what: str):
    """Common gate for anything a staff member does to one ticket: signed in? ticket exists? Cedar says yes?
    Returns (principal, ticket dict, decision, None) or (None, None, None, (error body, status))."""
    principal = session.verify(token)
    if principal is None:
        return None, None, None, ({"error": "Not signed in."}, 401)
    row = get_store().get_ticket(ticket_id)
    if row is None:
        return None, None, None, ({"error": "Unknown ticket."}, 404)
    try:
        d = cedar_authz.authorize(_cedar_principal(principal), action, "Ticket", ticket_id,
                                  {"brand": brand_for(row["product_id"]).lower(), "safety": bool(row.get("safety_flag"))})
    except CedarUnavailable as exc:
        return None, None, None, ({"error": f"Authorization check unavailable: {exc}"}, 503)
    if not d.allowed:
        obs.logger.warning("authz_denied", action=action, principal_brand=principal.brand, role=principal.role, policies=d.policies)
        return None, None, None, ({"error": _deny_message(principal, f"{what} {ticket_id}", d), "decision": {"allowed": False, "policies": d.policies}}, 403)
    return principal, row, d, None


def update_ticket_status(ticket_id: str, status: str, token: str | None) -> tuple[dict, int]:
    principal, row, d, err = _ticket_access(token, ticket_id, "updateTicketStatus", "change ticket")
    if err:
        return err
    if status not in TICKET_STATUSES:
        return {"error": f"status must be one of {TICKET_STATUSES}"}, 400
    ticket = Ticket(**row)
    ticket.status = status
    ticket.save()
    if status == "resolved":
        from src.channel import bot
        bot.ticket_resolved(row, principal.name)
    return {"ticket_id": ticket_id, "status": status, "decision": {"allowed": True, "policies": d.policies}}, 200


def ticket_reply(ticket_id: str, text: str, token: str | None) -> tuple[dict, int]:
    """A person answers the customer, on WhatsApp, from the brand's inbox."""
    principal, row, d, err = _ticket_access(token, ticket_id, "replyToCustomer", "reply on ticket")
    if err:
        return err
    text = (text or "").strip()
    if not text:
        return {"error": "Write a message first."}, 400
    from src.channel import bot
    msg = bot.staff_reply(row, text[:1000], principal.name)
    if row.get("status") == "new":
        t = Ticket(**row)
        t.status = "in_progress"
        t.save()
    return {"sent": msg, "decision": {"allowed": True, "policies": d.policies}}, 200


def ticket_thread(ticket_id: str, token: str | None) -> tuple[dict, int]:
    """The whole WhatsApp conversation behind a ticket (never exposes the phone number)."""
    principal, row, d, err = _ticket_access(token, ticket_id, "viewTicket", "view ticket")
    if err:
        return err
    brand = brand_for(row["product_id"]).lower()
    return {"ticket": {"ticket_id": ticket_id, "status": row.get("status"), "customer_name": row["customer_name"],
                       "product_name": row["product_name"], "reason_label": agent_mod.ESCALATION_LABELS.get(row.get("reason_code", ""), ""),
                       "safety_flag": bool(row.get("safety_flag"))},
            "messages": get_store().chat_messages(brand, row["customer_phone"])}, 200


def inbox(brand: str, token: str | None) -> tuple[dict, int]:
    """The brand's WhatsApp inbox: every chat on its line, handed-over ones first."""
    brand = brand.strip().lower()
    principal = session.verify(token)
    if principal is None:
        return {"error": "Not signed in."}, 401
    try:
        decision = cedar_authz.can_view_dashboard(_cedar_principal(principal), brand)
    except CedarUnavailable as exc:
        return {"error": f"Authorization check unavailable: {exc}"}, 503
    if not decision.allowed:
        return {"error": _deny_message(principal, f"view {brand}'s inbox", decision), "decision": {"allowed": False, "policies": decision.policies}}, 403
    rows = []
    for c in get_store().chat_index(brand):
        t = get_store().get_ticket(c["ticket_id"]) if c.get("ticket_id") else None
        rows.append({"customer_name": c["customer_name"], "phone": mask_phone(c["phone"]), "last_text": c["last_text"], "mode": c["mode"],
                     "ticket_id": c.get("ticket_id", ""), "reason": agent_mod.ESCALATION_LABELS.get(c.get("reason", ""), c.get("reason", "")), "unread": c.get("unread", 0),
                     "updated_at": c["updated_at"], "ticket_status": (t or {}).get("status", ""), "safety": bool((t or {}).get("safety_flag"))})
    rows.sort(key=lambda r: (r["mode"] != "human" or r["ticket_status"] == "resolved", r["updated_at"]), reverse=False)
    handed = sorted([r for r in rows if r["mode"] == "human" and r["ticket_status"] != "resolved"], key=lambda r: r["updated_at"], reverse=True)
    rest = sorted([r for r in rows if r not in handed], key=lambda r: r["updated_at"], reverse=True)
    return {"principal": asdict(principal), "chats": handed + rest}, 200


def wa_messages(brand: str, phone: str, after: str = "") -> dict:
    """What the customer's phone shows. No login: it stands in for the customer's own device."""
    phone = phone.strip()
    if phone and not phone.startswith("+"):
        phone = "+" + phone
    return {"messages": get_store().chat_messages(brand.strip().lower(), phone, after)}


def wa_webhook(payload: dict) -> tuple[dict, int]:
    from src.channel import bot
    replies = []
    for brand, phone, inbound in bot.parse_webhook(payload):
        replies.extend(bot.handle_inbound(brand, phone, inbound))
    return {"status": "ok", "replies": replies}, 200


def sandbox_customers() -> list[dict]:
    """Everyone in the registry, grouped by phone: what the sandbox's 'send as' picker offers."""
    seen: dict[str, dict] = {}
    for b in BRAND_SLUGS:
        for r in regs_for_brand(b.lower()):
            c = seen.setdefault(r.customer_phone, {"phone": r.customer_phone, "name": r.customer_name, "products": []})
            c["products"].append({"brand": brand_for(r.product_id).lower(), "product_name": r.product_name, "serial": r.serial_number,
                                  "purchase_date": r.purchase_date, "warranty_component_status": r.warranty_component_status})
    return sorted(seen.values(), key=lambda c: c["name"])


def sandbox_reset() -> dict:
    """Wipe everything a demo run produced (conversations, tickets, chats, cases) and the orders the
    sandbox uploaded. The baseline registry stays."""
    n = get_store().clear() + get_store().delete_registrations("sandbox")
    case_index.reset()
    return {"cleared": n}


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
    if code == "human_requested":
        return (f"Of course. I've passed this to our service team as ticket {tid}, with your details attached. "
                f"A person will reply to you here on WhatsApp.")
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
    if conv.answered:
        return {"status": "answered", "message": conv.answer, "meta": meta}
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
