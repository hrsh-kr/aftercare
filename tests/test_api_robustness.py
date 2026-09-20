"""Bad input gets a clean 4xx, never a stack trace or a crash. No services needed."""
import os
import sys

os.environ["AFTERCARE_STORE"] = "file"

from tests.lambda_client import Client

c = Client()


def test_malformed_and_non_object_json_is_400():
    assert c.call("POST", "/api/start", body="garbage").status_code == 400
    assert c.call("POST", "/api/start", body="[1, 2]").status_code == 400
    assert c.call("POST", "/api/login", body="{").status_code == 400


def test_missing_and_wrong_typed_fields_are_handled():
    assert c.post("/api/start", json={"phone": "x", "complaint": "y"}).status_code == 400
    assert c.post("/api/login", json={"username": 123, "passcode": None}).status_code == 401
    assert c.post("/api/login", json={}).status_code == 401


def test_staff_routes_need_a_session():
    for method, path in [("GET", "/api/me"), ("GET", "/api/dashboard/aquaspin"), ("GET", "/api/inbox/aquaspin"),
                         ("POST", "/api/tickets/TBB-1/reply"), ("POST", "/api/tickets/TBB-1/status"), ("GET", "/api/tickets/TBB-1/thread")]:
        assert c.call(method, path, body={} if method == "POST" else None).status_code == 401, path


def test_a_webhook_without_a_message_body_is_ignored_not_fatal():
    payload = {"entry": [{"changes": [{"value": {"metadata": {"display_phone_number": "+91 1800 000 0001"},
                                                  "messages": [{"from": "9199", "type": "text", "text": {}}]}}]}]}
    r = c.post("/api/wa/webhook", json=payload)
    assert r.status_code == 200 and r.json["replies"] == []


def test_ingest_rejects_garbage_with_a_reason():
    assert c.call("POST", "/api/ingest", body="not,a,csv").status_code == 422


if __name__ == "__main__":
    fails = 0
    for name, fn in [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]:
        try:
            fn(); print("PASS ", name)
        except AssertionError as e:
            fails += 1; print("FAIL ", name, e)
    print("all passed" if not fails else f"{fails} failed")
    sys.exit(1 if fails else 0)
