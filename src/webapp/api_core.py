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
"""

import json
import os
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.authz.cedar_authz import CedarUnavailable, can_view_dashboard
from src.layer1.registration import Registration, load_registrations, lookup_by_phone
from src.layer2 import agent as agent_mod
from src.layer3b.tickets import Ticket

_agent = None  # built lazily, once, on first use -- avoids paying Ollama startup cost at import time
# Same AFTERCARE_DATA_DIR override as tickets.py -- /var/task is
# read-only under real Lambda (and SAM Local), only /tmp is writable.
CONV_DIR = Path(os.environ.get("AFTERCARE_DATA_DIR", str(Path(__file__).resolve().parent.parent.parent / "data"))) / "conversations"


def get_agent():
    global _agent
    if _agent is None:
        _agent = agent_mod._build_agent()
    return _agent


def _save_conversation(conv_id: str, conv: agent_mod.Conversation) -> None:
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    (CONV_DIR / f"{conv_id}.json").write_text(json.dumps(asdict(conv), indent=2))


def _load_conversation(conv_id: str) -> agent_mod.Conversation | None:
    path = CONV_DIR / f"{conv_id}.json"
    if not conv_id or not path.exists():
        return None
    data = json.loads(path.read_text())
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
    )


def list_customers() -> list[dict]:
    """For the demo's 'simulate as' picker only. A real WhatsApp
    integration never needs this -- the incoming message already
    carries the sender's number, per WhatsApp's own webhook payload."""
    seen = {}
    for r in load_registrations():
        seen.setdefault(r.customer_phone, r.customer_name)
    return [{"phone": phone, "name": name} for phone, name in seen.items()]


def lookup(phone: str) -> dict:
    regs = lookup_by_phone(phone, load_registrations())
    if not regs:
        return {"found": False}
    return {
        "found": True,
        "customer_name": regs[0].customer_name,
        "brand": agent_mod.brand_for(regs[0].product_id),
        "products": [
            {"product_id": r.product_id, "product_name": r.product_name, "serial_number": r.serial_number}
            for r in regs
        ],
    }


def start_conversation(phone: str, complaint: str) -> tuple[dict, int]:
    regs = lookup_by_phone(phone, load_registrations())
    if not regs:
        return {"error": "No registration found for this number."}, 404

    conv = agent_mod.start(regs[0], complaint, agent=get_agent())
    conv_id = str(uuid.uuid4())
    _save_conversation(conv_id, conv)
    return {"conversation_id": conv_id, **_conversation_state(conv)}, 200


def respond_conversation(conversation_id: str, reply: str) -> tuple[dict, int]:
    conv = _load_conversation(conversation_id)
    if conv is None:
        return {"error": "Unknown conversation."}, 404

    conv = agent_mod.respond(conv, reply, agent=get_agent())
    _save_conversation(conversation_id, conv)
    return _conversation_state(conv), 200


def dashboard_data(brand: str, staff_brand: str) -> tuple[dict, int]:
    """Brand-scoped, Cedar-authorized. staff_brand is who the request
    claims to be logged in as; brand is whose data is being asked for.
    These can disagree -- e.g. an ArcticAir staff session asking for
    aquaspin's dashboard -- and Cedar is what actually decides, not an
    if-statement guessing at the same logic."""
    brand = brand.strip().lower()
    staff_brand = staff_brand.strip().lower()

    try:
        allowed = can_view_dashboard(staff_brand, brand)
    except CedarUnavailable as exc:
        return {"error": f"Authorization check unavailable: {exc}"}, 503

    if not allowed:
        return {"error": f"Not authorized to view {brand}'s dashboard as '{staff_brand or 'nobody'}'."}, 403

    registrations = [r for r in load_registrations() if agent_mod.brand_for(r.product_id).lower() == brand]
    tickets = sorted(
        [t for t in Ticket.load_all() if t.product_id and agent_mod.brand_for(t.product_id).lower() == brand],
        key=lambda t: t.ticket_id,
    )

    warranty_counts = {"active": 0, "expired": 0}
    for r in registrations:
        warranty_counts["active" if r.warranty_component_status == "active" else "expired"] += 1
        warranty_counts["active" if r.warranty_parts_status == "active" else "expired"] += 1

    product_feedback: dict[str, int] = {}
    for t in tickets:
        product_feedback[t.product_name] = product_feedback.get(t.product_name, 0) + 1

    return {
        "brand": brand,
        "tickets": [
            {
                "ticket_id": t.ticket_id,
                "customer_name": t.customer_name,
                "product_name": t.product_name,
                "issue_summary": t.issue_summary,
                "attempts_tried": t.attempts_tried,
                "safety_flag": t.safety_flag,
                "status": t.status,
                "created_at": t.created_at,
            }
            for t in tickets
        ],
        "warranty_counts": warranty_counts,
        "product_feedback": [{"product_name": k, "count": v} for k, v in sorted(product_feedback.items(), key=lambda kv: -kv[1])],
        "registered_count": len(registrations),
    }, 200


def _clean(message: str) -> str:
    """The model occasionally wraps its answer in quote marks despite
    being asked not to add anything extra -- strip them rather than
    show the customer a stray quoted string."""
    return message.strip().strip('"').strip()


def _conversation_state(conv: agent_mod.Conversation) -> dict:
    """What the frontend needs to render the next thing to show."""
    if conv.resolved:
        return {"status": "resolved", "message": "Glad that fixed it! Let us know if anything else comes up."}
    if conv.ticket is not None:
        return {
            "status": "escalated",
            "message": (
                f"I've created ticket {conv.ticket.ticket_id} for you and looped in our service team. "
                f"They'll follow up within 5 business days."
            ),
            "ticket_id": conv.ticket.ticket_id,
        }
    return {"status": "waiting", "message": _clean(conv.turns[-1].step)}
