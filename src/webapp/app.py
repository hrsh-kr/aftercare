"""Phase 5: the customer-facing chat UI's backend. A simulated
channel (see DESIGN.md) -- the logic underneath is fully real.

Conversation state kept in memory, keyed by a generated id -- fine
for a hackathon demo, not meant to survive a restart.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from flask import Flask, abort, jsonify, render_template, request

from src.authz.cedar_authz import CedarUnavailable, can_view_dashboard
from src.layer1.registration import load_registrations, lookup_by_phone
from src.layer2 import agent as agent_mod
from src.layer3b.tickets import Ticket

app = Flask(__name__)
_agent = None  # built lazily, once, on first request -- avoids paying Ollama startup cost at import time
_conversations: dict[str, agent_mod.Conversation] = {}


def get_agent():
    global _agent
    if _agent is None:
        _agent = agent_mod._build_agent()
    return _agent


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard_login():
    """The 'which brand's staff am I' picker -- same honesty pattern as
    the customer picker on '/': a real login system would already know
    who's signed in, this is a browser demo standing in for that. Picks
    who Cedar treats as the principal for every dashboard call that follows."""
    return render_template("dashboard_login.html", brands=agent_mod.BRAND_SLUGS)


@app.route("/dashboard/<brand>")
def dashboard(brand: str):
    brand = brand.strip().lower()
    if brand not in agent_mod.BRAND_SLUGS:
        abort(404)
    return render_template("dashboard.html", brand=brand, brand_display=agent_mod.BRAND_SLUGS[brand])


@app.route("/api/dashboard/<brand>", methods=["GET"])
def dashboard_data(brand: str):
    """Brand-scoped, Cedar-authorized. staff_brand is who the request
    claims to be logged in as (the dashboard login picker); brand is
    whose data is being asked for, straight from the URL. These can
    disagree -- e.g. an ArcticAir staff session hitting
    /api/dashboard/aquaspin directly -- and Cedar is what actually
    decides, not a Python if-statement guessing at the same logic."""
    staff_brand = request.headers.get("X-Staff-Brand", "").strip().lower()
    brand = brand.strip().lower()

    try:
        allowed = can_view_dashboard(staff_brand, brand)
    except CedarUnavailable as exc:
        return jsonify({"error": f"Authorization check unavailable: {exc}"}), 503

    if not allowed:
        return jsonify({"error": f"Not authorized to view {brand}'s dashboard as '{staff_brand or 'nobody'}'."}), 403

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

    return jsonify(
        {
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
        }
    )


@app.route("/api/customers", methods=["GET"])
def customers():
    """For the demo's 'simulate as' picker only. A real WhatsApp
    integration never needs this -- the incoming message already
    carries the sender's number, per WhatsApp's own webhook payload.
    This endpoint exists purely because a browser demo has no real
    phone attached to it."""
    seen = {}
    for r in load_registrations():
        seen.setdefault(r.customer_phone, r.customer_name)
    return jsonify([{"phone": phone, "name": name} for phone, name in seen.items()])


@app.route("/api/lookup", methods=["POST"])
def lookup():
    phone = request.json.get("phone", "").strip()
    regs = lookup_by_phone(phone, load_registrations())
    if not regs:
        return jsonify({"found": False})
    return jsonify(
        {
            "found": True,
            "customer_name": regs[0].customer_name,
            "brand": agent_mod.brand_for(regs[0].product_id),
            "products": [
                {"product_id": r.product_id, "product_name": r.product_name, "serial_number": r.serial_number}
                for r in regs
            ],
        }
    )


@app.route("/api/start", methods=["POST"])
def start():
    phone = request.json.get("phone", "").strip()
    complaint = request.json.get("complaint", "").strip()
    regs = lookup_by_phone(phone, load_registrations())
    if not regs:
        return jsonify({"error": "No registration found for this number."}), 404

    conv = agent_mod.start(regs[0], complaint, agent=get_agent())
    conv_id = str(uuid.uuid4())
    _conversations[conv_id] = conv
    return jsonify({"conversation_id": conv_id, **_conversation_state(conv)})


@app.route("/api/respond", methods=["POST"])
def respond():
    conv_id = request.json.get("conversation_id")
    reply = request.json.get("reply", "").strip()
    conv = _conversations.get(conv_id)
    if conv is None:
        return jsonify({"error": "Unknown conversation."}), 404

    conv = agent_mod.respond(conv, reply, agent=get_agent())
    return jsonify(_conversation_state(conv))


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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
