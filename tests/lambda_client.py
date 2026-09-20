"""Call the deployed-shape Lambda (src.lambda_app.handler) with API Gateway proxy events, in process.
No web framework, no network: the same event the real API Gateway would send."""
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse


class Ctx:
    function_name = "WebFunction"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:ap-south-1:000000000000:function:WebFunction"
    aws_request_id = "test-request"

    def get_remaining_time_in_millis(self):
        return 120000


class Client:
    """Keeps cookies between calls, like a browser."""

    def __init__(self):
        self.cookie = ""

    def call(self, method, path, body=None, headers=None):
        from src import lambda_app
        url = urlparse(path)
        qs = {k: v[0] for k, v in parse_qs(url.query).items()} or None
        hdrs = {"Cookie": self.cookie, **(headers or {})} if self.cookie else dict(headers or {})
        event = {
            "resource": url.path, "path": url.path, "httpMethod": method, "headers": hdrs, "multiValueHeaders": {},
            "queryStringParameters": qs, "pathParameters": None, "isBase64Encoded": False,
            "body": json.dumps(body) if isinstance(body, (dict, list)) else body,
            "requestContext": {"requestId": "test", "stage": "prod", "path": url.path, "httpMethod": method, "accountId": "0", "apiId": "x"},
        }
        r = lambda_app.handler(event, Ctx())
        set_cookie = (r.get("headers") or {}).get("Set-Cookie") or ((r.get("multiValueHeaders") or {}).get("Set-Cookie") or [None])[0]
        if set_cookie:
            self.cookie = set_cookie.split(";")[0] if not set_cookie.split(";")[0].endswith("=") else ""
        merged = {**(r.get("headers") or {}), **{k: v[0] for k, v in (r.get("multiValueHeaders") or {}).items() if v}}
        text = r.get("body") or ""
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        return SimpleNamespace(status_code=r["statusCode"], json=data, text=text, headers=merged, raw=r)

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, json=None, **kw):
        return self.call("POST", path, body=json, **kw)
