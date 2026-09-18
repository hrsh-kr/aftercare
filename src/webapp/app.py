"""Flask adapter -- the live demo server. All real logic lives in
api_core.py, shared with the SAM Local Lambda handlers
(../lambda_handlers.py); this file only translates Flask's
request/response shape into calls there and back.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from flask import Flask, abort, jsonify, render_template, request

from src.layer2 import agent as agent_mod
from src.webapp import api_core as core

app = Flask(__name__)


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
    staff_brand = request.headers.get("X-Staff-Brand", "")
    data, status = core.dashboard_data(brand, staff_brand)
    return jsonify(data), status


@app.route("/api/customers", methods=["GET"])
def customers():
    return jsonify(core.list_customers())


@app.route("/api/lookup", methods=["POST"])
def lookup():
    phone = request.json.get("phone", "").strip()
    return jsonify(core.lookup(phone))


@app.route("/api/start", methods=["POST"])
def start():
    phone = request.json.get("phone", "").strip()
    complaint = request.json.get("complaint", "").strip()
    data, status = core.start_conversation(phone, complaint)
    return jsonify(data), status


@app.route("/api/respond", methods=["POST"])
def respond():
    conv_id = request.json.get("conversation_id")
    reply = request.json.get("reply", "").strip()
    data, status = core.respond_conversation(conv_id, reply)
    return jsonify(data), status


if __name__ == "__main__":
    app.run(debug=True, port=5001)
