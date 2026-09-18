"""Phase 5: the customer-facing chat UI's backend. A simulated
channel (see DESIGN.md) -- the logic underneath is fully real.

Conversation state kept in memory, keyed by a generated id -- fine
for a hackathon demo, not meant to survive a restart.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from flask import Flask, jsonify, render_template, request

from src.layer1.registration import load_registrations, lookup_by_phone
from src.layer2 import agent as agent_mod

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
