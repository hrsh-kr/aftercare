"""The whole web app as one AWS Lambda behind API Gateway: pages and API.

Routing uses Lambda Powertools' API Gateway resolver. All logic lives in api_core.py and pages.py;
this file only translates an API Gateway proxy event into calls there and back. There is no other
server: `sam local start-api` is the only way this app runs locally, and it is the same artifact
`sam deploy` would ship.
"""

import json

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types
from aws_lambda_powertools.event_handler.exceptions import BadRequestError

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
    """The JSON request body as a dict; anything else is a 400, not a crash."""
    try:
        body = app.current_event.json_body
    except ValueError as exc:
        raise BadRequestError("Request body is not valid JSON.") from exc
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise BadRequestError("Request body must be a JSON object.")
    return body


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


@app.exception_handler(BadRequestError)
def _bad_request(exc: BadRequestError):
    return _json({"error": exc.msg}, 400)


@app.exception_handler(Exception)
def _unexpected(exc: Exception):
    """Never leak a stack trace to the client; the log (with the request id) has it."""
    logger.exception("unhandled_error")
    return _json({"error": "Something went wrong on our side."}, 500)


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


@app.get("/sandbox")
def sandbox():
    return _html(pages.sandbox())


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
    return _json(core.lookup(_text(b.get("phone")), brand=_text(b.get("brand")).lower()))


@app.post("/api/start")
def start():
    b = _body()
    if not _text(b.get("product_id")):
        return _json({"error": "product_id is required"}, 400)
    key = app.current_event.get_header_value("Idempotency-Key", default_value="", case_sensitive=False) or None
    if key:
        from src.webapp import idempotency
        idempotency._config.register_lambda_context(app.lambda_context)
    try:
        data, status = core.start_conversation(_text(b.get("phone")), _text(b.get("complaint")),
                                               _text(b.get("product_id")), idempotency_key=key)
    except Exception as exc:
        if type(exc).__name__ == "IdempotencyValidationError":
            return _json({"error": "That Idempotency-Key was already used with a different request."}, 422)
        raise
    return _json(data, status)


@app.post("/api/respond")
def respond():
    b = _body()
    data, status = core.respond_conversation(_text(b.get("conversation_id")), _text(b.get("reply")))
    return _json(data, status)


@app.post("/api/login")
def login():
    b = _body()
    data, status = core.login(_text(b.get("username")), b.get("passcode") if isinstance(b.get("passcode"), str) else "")
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
    data, status = core.update_ticket_status(ticket_id, _text(_body().get("status")), _token())
    return _json(data, status)


@app.post("/api/ingest")
def ingest():
    data, status = core.ingest_preview(app.current_event.body or "")
    return _json(data, status)


@app.get("/api/sample-csv")
def sample_csv():
    from src.domain.registration import SALES_DATA
    return Response(status_code=200, content_type="text/csv", body=SALES_DATA.read_text())


@app.post("/api/demo/reset")
def demo_reset():
    import os
    if os.environ.get("AFTERCARE_DEMO") != "1":
        return _json({"error": "Not found."}, 404)
    return _json(core.reset_demo_data())


# ── WhatsApp channel + sandbox ────────────────────────────────────────────────
@app.post("/api/wa/webhook")
def wa_webhook():
    """Meta's WhatsApp Cloud API webhook shape: the door a real WhatsApp Business number would use."""
    data, status = core.wa_webhook(_body())
    return _json(data, status)


@app.get("/api/wa/messages")
def wa_messages():
    ev = app.current_event
    return _json(core.wa_messages(ev.get_query_string_value("brand", "") or "", ev.get_query_string_value("phone", "") or "",
                                  ev.get_query_string_value("after", "") or ""))


@app.get("/api/inbox/<brand>")
def inbox(brand: str):
    data, status = core.inbox(brand, _token())
    return _json(data, status)


@app.get("/api/tickets/<ticket_id>/thread")
def ticket_thread(ticket_id: str):
    data, status = core.ticket_thread(ticket_id, _token())
    return _json(data, status)


@app.post("/api/tickets/<ticket_id>/reply")
def ticket_reply(ticket_id: str):
    data, status = core.ticket_reply(ticket_id, _text(_body().get("text")), _token())
    return _json(data, status)


@app.get("/api/sandbox/customers")
def sandbox_customers():
    return _json(core.sandbox_customers())


_SAMPLES = {
    "orders_croma_sep2026.csv": "A multi-brand store's export (Croma): AquaSpin and ArcticAir sales mixed together, plus two rows that need fixing.",
    "orders_aquaspin_direct.csv": "A brand's own export (AquaSpin direct sales): clean, one brand.",
}


@app.get("/api/sandbox/samples")
def sandbox_samples():
    return _json([{"name": n, "about": a} for n, a in _SAMPLES.items()])


@app.get("/api/sandbox/samples/<name>")
def sandbox_sample(name: str):
    from src.domain.registration import FIXTURES
    if name not in _SAMPLES:
        return _json({"error": "Unknown sample."}, 404)
    return Response(status_code=200, content_type="text/csv", body=(FIXTURES / "sandbox" / name).read_text())


@app.post("/api/sandbox/ingest")
def sandbox_ingest():
    data, status = core.ingest_commit(app.current_event.body or "", source="sandbox")
    return _json(data, status)


@app.post("/api/sandbox/reset")
def sandbox_reset():
    import os
    if os.environ.get("AFTERCARE_DEMO") != "1":
        return _json({"error": "Not found."}, 404)
    return _json(core.sandbox_reset())


@logger.inject_lambda_context(correlation_id_path="requestContext.requestId")
def handler(event, context):
    return app.resolve(event, context)
