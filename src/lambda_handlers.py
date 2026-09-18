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


def _response(body: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    return json.loads(raw)


def _header(event: dict, name: str) -> str:
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def customers(event, context):
    return _response(core.list_customers())


def lookup(event, context):
    phone = _body(event).get("phone", "").strip()
    return _response(core.lookup(phone))


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
        data, status = core.start_conversation(body.get("phone", "").strip(), body.get("complaint", "").strip())
    return _response(data, status)


def dashboard(event, context):
    brand = (event.get("pathParameters") or {}).get("brand", "")
    staff_brand = _header(event, "X-Staff-Brand")
    data, status = core.dashboard_data(brand, staff_brand)
    return _response(data, status)
