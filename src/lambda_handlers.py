"""Lambda handlers for SAM Local -- same core logic as the Flask app
(src/webapp/api_core.py, what the live demo actually runs), wrapped for
API Gateway's proxy-integration event shape. Run locally, no AWS
account, no deployment -- this exists to prove the logic is
serverless-ready, not to replace the Flask demo.

    sam build --use-container   # container build: this host may not match
                                 # Lambda's python3.12/linux/arm64 runtime
    sam local start-api --warm-containers LAZY   # LAZY: /api/start and
                                 # /api/respond share one function's warm
                                 # container, see conversation()'s docstring
    curl http://127.0.0.1:3000/api/customers
"""

import json

from src.webapp import api_core as core


def _response(body: dict, status: int = 200, cookie: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Set-Cookie"] = cookie
    return {"statusCode": status, "headers": headers, "body": json.dumps(body)}


def _token(event: dict) -> str | None:
    """The session cookie, from API Gateway's Cookie header."""
    from src.authz import session
    for part in _header(event, "Cookie").split(";"):
        name, _, value = part.strip().partition("=")
        if name == session.COOKIE:
            return value
    return None


def _body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    return json.loads(raw)


def _register_idempotency_context(context) -> None:
    """Lets Powertools stop early rather than leave an in-progress record if Lambda is about to time out."""
    try:
        from src.webapp import idempotency
        idempotency._config.register_lambda_context(context)
    except Exception:
        pass


def _header(event: dict, name: str) -> str:
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def customers(event, context):
    # ?brand= query param scopes the list to that brand's customers only
    qs = event.get("queryStringParameters") or {}
    brand = qs.get("brand", "").strip().lower()
    return _response(core.list_customers(brand=brand))


def lookup(event, context):
    body = _body(event)
    phone = body.get("phone", "").strip()
    brand = body.get("brand", "").strip().lower()
    return _response(core.lookup(phone, brand=brand))


def conversation(event, context):
    """Handles both /api/start and /api/respond -- one Lambda function,
    not two. They need to share a warm container's writable /tmp (see
    api_core.py's AFTERCARE_DATA_DIR) to carry a conversation across
    turns; two separate functions each get their own container and
    never actually share state, found by testing this against SAM
    Local for real (see IMPLEMENTATION.md Phase 7.5). Run with
    `sam local start-api --warm-containers LAZY` so the container (and
    its /tmp) actually persists between the start and respond calls.

    A real production deployment would back this with DynamoDB instead
    of relying on warm-container reuse, which AWS never guarantees --
    same "plain Python stands in for the real AWS service" pattern as
    the rest of this build under Build It."""
    body = _body(event)
    path = event.get("path", "")
    if path.endswith("/respond"):
        data, status = core.respond_conversation(body.get("conversation_id"), body.get("reply", "").strip())
    else:
        _register_idempotency_context(context)
        # product_id is now required -- the customer selected which product they
        # need help with before reaching this call. regs[0] is gone.
        try:
            data, status = core.start_conversation(
                body.get("phone", "").strip(),
                body.get("complaint", "").strip(),
                body.get("product_id", "").strip(),
                idempotency_key=_header(event, "Idempotency-Key") or None,
            )
        except Exception as exc:
            if type(exc).__name__ == "IdempotencyValidationError":
                return _response({"error": "That Idempotency-Key was already used with a different request."}, 422)
            raise
    return _response(data, status)


def dashboard(event, context):
    brand = (event.get("pathParameters") or {}).get("brand", "")
    q = (event.get("queryStringParameters") or {}).get("q", "")
    data, status = core.dashboard_data(brand, _token(event), q)
    return _response(data, status)


def login(event, context):
    from src.authz import session
    body = _body(event)
    data, status = core.login(body.get("username", ""), body.get("passcode", ""))
    token = data.pop("token", None)
    cookie = f"{session.COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={session.MAX_AGE}" if token else None
    return _response(data, status, cookie)


def me(event, context):
    data, status = core.me(_token(event))
    return _response(data, status)


def ticket_status(event, context):
    ticket_id = (event.get("pathParameters") or {}).get("ticket_id", "")
    data, status = core.update_ticket_status(ticket_id, _body(event).get("status", ""), _token(event))
    return _response(data, status)


def health(event, context):
    return _response(core.health())


def demo_reset(event, context):
    """Local demos only: refuses unless AFTERCARE_DEMO=1 (set in template.yaml for sam local,
    which a real deployment must not do)."""
    import os
    if os.environ.get("AFTERCARE_DEMO") != "1":
        return _response({"error": "Not found."}, 404)
    return _response(core.reset_demo_data())


def ingest(event, context):
    data, status = core.ingest_preview(event.get("body") or "")
    return _response(data, status)
