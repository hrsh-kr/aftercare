"""Flask adapter -- the live demo server. All real logic lives in
api_core.py, shared with the SAM Local Lambda handlers
(../lambda_handlers.py); this file only translates Flask's
request/response shape into calls there and back.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from flask import Flask, abort, jsonify, render_template, request

from src.layer1.catalog import brand_for
from src.layer1.registration import load_registrations
from src.layer2 import agent as agent_mod
from src.webapp import api_core as core

app = Flask(__name__)


_mask_phone = core.mask_phone


@app.route("/")
def landing():
    """The one-page story: hook -> Step 0 (a brand or store uploads its sales
    CSV, Aftercare sorts it by brand and connects the WhatsApp line) -> the
    customer's journey -> live demo. Step 0 renders the real fixture rows
    (phones masked), the brand each product code maps to (catalog.py), and
    real per-brand counts -- nothing invented."""
    regs = load_registrations()
    rows = [
        {
            "customer": r.customer_name,
            "phone": _mask_phone(r.customer_phone),
            "product": r.product_name,
            "serial": r.serial_number,
            "purchased": r.purchase_date,
            "brand": brand_for(r.product_id),
        }
        for r in regs
    ]
    by_brand: dict[str, dict] = {}
    for r in regs:
        name = brand_for(r.product_id)
        entry = by_brand.setdefault(name, {"name": name, "slug": name.lower(), "products": 0, "phones": set()})
        entry["products"] += 1
        entry["phones"].add(r.customer_phone)
    brand_stats = [
        {"name": e["name"], "slug": e["slug"], "products": e["products"], "customers": len(e["phones"])}
        for e in sorted(by_brand.values(), key=lambda e: e["name"])
    ]
    stats = {
        "products": len(regs),
        "customers": len({r.customer_phone for r in regs}),
        "brands": len(brand_stats),
    }
    return render_template("landing.html", rows=rows, stats=stats, brand_stats=brand_stats)


@app.route("/demo")
def demo():
    """The brand-scoped two-pane WhatsApp demo UI."""
    return render_template("demo.html")


@app.route("/dashboard")
def dashboard_login():
    """Staff sign-in: pick an account, enter its passcode (server issues the session)."""
    from src.authz import session
    return render_template("dashboard_login.html", staff=session.staff_directory(), brands=agent_mod.BRAND_SLUGS)


@app.route("/dashboard/<brand>")
def dashboard(brand: str):
    brand = brand.strip().lower()
    if brand not in agent_mod.BRAND_SLUGS:
        abort(404)
    others = [(k, v) for k, v in agent_mod.BRAND_SLUGS.items() if k != brand]
    return render_template("dashboard.html", brand=brand, brand_display=agent_mod.BRAND_SLUGS[brand], others=others)


def _token() -> str | None:
    from src.authz import session
    return request.cookies.get(session.COOKIE)


@app.route("/api/login", methods=["POST"])
def login():
    from src.authz import session
    body = request.get_json(silent=True) or {}
    data, status = core.login(body.get("username", ""), body.get("passcode", ""))
    token = data.pop("token", None)
    resp = jsonify(data)
    resp.status_code = status
    if token:
        resp.set_cookie(session.COOKIE, token, httponly=True, samesite="Lax", max_age=session.MAX_AGE)
    return resp


@app.route("/api/logout", methods=["POST"])
def logout():
    from src.authz import session
    resp = jsonify({"ok": True})
    resp.delete_cookie(session.COOKIE)
    return resp


@app.route("/api/me", methods=["GET"])
def me():
    data, status = core.me(_token())
    return jsonify(data), status


@app.route("/api/dashboard/<brand>", methods=["GET"])
def dashboard_data(brand: str):
    data, status = core.dashboard_data(brand, _token(), request.args.get("q", ""))
    return jsonify(data), status


@app.route("/api/tickets/<ticket_id>/status", methods=["POST"])
def ticket_status(ticket_id: str):
    data, status = core.update_ticket_status(ticket_id, (request.get_json(silent=True) or {}).get("status", ""), _token())
    return jsonify(data), status


@app.route("/api/customers", methods=["GET"])
def customers():
    """Returns customers filtered to a brand if ?brand= is supplied.
    The demo is brand-scoped -- each brand's WhatsApp line sees only
    its own customers."""
    brand = request.args.get("brand", "").strip().lower()
    return jsonify(core.list_customers(brand=brand))


@app.route("/api/lookup", methods=["POST"])
def lookup():
    """Lookup a customer by phone, scoped to a brand.
    brand comes from the demo session (which brand's line the user
    is simulating) -- not guessed from the registration data."""
    phone = request.json.get("phone", "").strip()
    brand = request.json.get("brand", "").strip().lower()
    return jsonify(core.lookup(phone, brand=brand))


@app.route("/api/start", methods=["POST"])
def start():
    """Start a conversation. product_id is now required -- the customer
    has selected which product they need help with. Using regs[0] was
    wrong and is now gone from the codebase."""
    phone = request.json.get("phone", "").strip()
    complaint = request.json.get("complaint", "").strip()
    product_id = request.json.get("product_id", "").strip()
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400
    data, status = core.start_conversation(phone, complaint, product_id)
    return jsonify(data), status


@app.route("/api/respond", methods=["POST"])
def respond():
    conv_id = request.json.get("conversation_id")
    reply = request.json.get("reply", "").strip()
    data, status = core.respond_conversation(conv_id, reply)
    return jsonify(data), status


@app.route("/api/sample-csv", methods=["GET"])
def sample_csv():
    """The fixture file the landing page's table is drawn from, so 'check the file above' checks exactly that file."""
    from src.layer1.registration import SALES_DATA
    return SALES_DATA.read_text(), 200, {"Content-Type": "text/csv"}


@app.route("/api/ingest", methods=["POST"])
def ingest():
    data, status = core.ingest_preview(request.get_data(as_text=True))
    return jsonify(data), status


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(core.health())


@app.route("/api/demo/reset", methods=["POST"])
def demo_reset():
    """Flask-only (not a Lambda route): wipe demo conversations and tickets so
    a run starts clean and doesn't look like a recurring issue to the next."""
    return jsonify(core.reset_demo_data())


if __name__ == "__main__":
    app.run(debug=True, port=5001)
