"""The whole web app as one AWS Lambda behind API Gateway: pages and API.

Routing uses Lambda Powertools' API Gateway resolver. All logic lives in api_core.py and pages.py;
this file only translates an API Gateway proxy event into calls there and back. There is no other
server: `sam local start-api` is the only way this app runs locally, and it is the same artifact
`sam deploy` would ship.
"""

import json

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types

from src import pages
from src.authz import session
from src.errors import DependencyUnavailable
from src.webapp import api_core as core
from src.webapp.observability import logger

app = APIGatewayRestResolver()


def _json(body: dict | list, status: int = 200, headers: dict | None = None) -> Response:
    return Response(status_code=status, content_type=content_types.APPLICATION_JSON, body=json.dumps(body), headers=headers or {})


def _html(body: str | None, status: int = 200) -> Response:
    if body is None:
        return Response(status_code=404, content_type=content_types.TEXT_HTML, body="<h1>Not found</h1>")
    return Response(status_code=status, content_type=content_types.TEXT_HTML, body=body)


def _token() -> str | None:
    cookie = app.current_event.get_header_value("Cookie", default_value="", case_sensitive=False) or ""
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == session.COOKIE:
            return value
    return None


def _body() -> dict:
    return app.current_event.json_body or {}


@app.exception_handler(DependencyUnavailable)
def _unavailable(exc: DependencyUnavailable):
    logger.error("dependency_unavailable", service=exc.service, detail=exc.detail)
    return _json({"error": str(exc), "service": exc.service}, 503)


# ── pages ────────────────────────────────────────────────────────────────────
@app.get("/")
def landing():
    return _html(pages.landing())


@app.get("/demo")
def demo():
    return _html(pages.demo())


@app.get("/dashboard")
def dashboard_login():
    return _html(pages.dashboard_login())


@app.get("/dashboard/<brand>")
def dashboard(brand: str):
    return _html(pages.dashboard(brand))


# ── API ──────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return _json(core.health())


@app.get("/api/customers")
def customers():
    return _json(core.list_customers(brand=(app.current_event.get_query_string_value("brand", "") or "").strip().lower()))


@app.post("/api/lookup")
def lookup():
    b = _body()
    return _json(core.lookup(b.get("phone", "").strip(), brand=b.get("brand", "").strip().lower()))


@app.post("/api/start")
def start():
    b = _body()
    if not b.get("product_id", "").strip():
        return _json({"error": "product_id is required"}, 400)
    key = app.current_event.get_header_value("Idempotency-Key", default_value="", case_sensitive=False) or None
    if key:
        from src.webapp import idempotency
        idempotency._config.register_lambda_context(app.lambda_context)
    try:
        data, status = core.start_conversation(b.get("phone", "").strip(), b.get("complaint", "").strip(),
                                               b["product_id"].strip(), idempotency_key=key)
    except Exception as exc:
        if type(exc).__name__ == "IdempotencyValidationError":
            return _json({"error": "That Idempotency-Key was already used with a different request."}, 422)
        raise
    return _json(data, status)


@app.post("/api/respond")
def respond():
    b = _body()
    data, status = core.respond_conversation(b.get("conversation_id"), b.get("reply", "").strip())
    return _json(data, status)


@app.post("/api/login")
def login():
    b = _body()
    data, status = core.login(b.get("username", ""), b.get("passcode", ""))
    token = data.pop("token", None)
    headers = {"Set-Cookie": f"{session.COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={session.MAX_AGE}"} if token else {}
    return _json(data, status, headers)


@app.post("/api/logout")
def logout():
    return _json({"ok": True}, 200, {"Set-Cookie": f"{session.COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"})


@app.get("/api/me")
def me():
    data, status = core.me(_token())
    return _json(data, status)


@app.get("/api/dashboard/<brand>")
def dashboard_data(brand: str):
    data, status = core.dashboard_data(brand, _token(), app.current_event.get_query_string_value("q", "") or "")
    return _json(data, status)


@app.post("/api/tickets/<ticket_id>/status")
def ticket_status(ticket_id: str):
    data, status = core.update_ticket_status(ticket_id, _body().get("status", ""), _token())
    return _json(data, status)


@app.post("/api/ingest")
def ingest():
    data, status = core.ingest_preview(app.current_event.body or "")
    return _json(data, status)


@app.get("/api/sample-csv")
def sample_csv():
    from src.layer1.registration import SALES_DATA
    return Response(status_code=200, content_type="text/csv", body=SALES_DATA.read_text())


@app.post("/api/demo/reset")
def demo_reset():
    import os
    if os.environ.get("AFTERCARE_DEMO") != "1":
        return _json({"error": "Not found."}, 404)
    return _json(core.reset_demo_data())


@logger.inject_lambda_context(correlation_id_path="requestContext.requestId")
def handler(event, context):
    return app.resolve(event, context)
