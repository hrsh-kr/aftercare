"""Run the five demo scenarios against any Aftercare API (sam local, http://127.0.0.1:3000)
and check each ends as its card promises. Uses the real model, so it takes a minute.

    .venv/bin/python scripts/run_scenarios.py http://127.0.0.1:3000
Clear old runs first (POST /api/demo/reset) or the
'fixed' scenario will look like a recurring issue."""
import sys
import uuid

import requests

API = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000").rstrip("/")
# (name, phone, product, complaint, replies, expected final status, expected reason code)
SCENARIOS = [
    ("fixed", "+919876543210", "WM-FC-700", "My washing machine bangs loudly when it spins", ["That fixed it, thank you!"], "resolved", None),
    ("two steps", "+919812345678", "AC-CB-15T", "My AC is on but the room isn't cooling", ["Still blowing warm air", "Still not cooling, no change"], "escalated", "attempts_exhausted"),
    ("not in manual", "+919876543210", "WM-FC-700", "The touch panel flickers and won't respond", [], "escalated", "unmatched"),
    ("recurring", "+919845098450", "WM-FC-700", "My washing machine bangs loudly when it spins", [], "escalated", "recurring"),
    ("safety", "+919900112233", "AC-CB-15T", "There's a burning smell coming from my AC", [], "escalated", "safety"),
]


def post(path, body, key=None):
    r = requests.post(API + path, json=body, headers={"Idempotency-Key": key} if key else {}, timeout=300)
    return r.status_code, r.json()


def main() -> int:
    bad = 0
    for name, phone, pid, complaint, replies, want, want_code in SCENARIOS:
        code, r = post("/api/start", {"phone": phone, "complaint": complaint, "product_id": pid}, key=str(uuid.uuid4()))
        cid = r.get("conversation_id")
        for reply in replies:
            if r.get("status") == "waiting":
                code, r = post("/api/respond", {"conversation_id": cid, "reply": reply})
        got = r.get("status")
        got_code = ((r.get("meta") or {}).get("escalation") or {}).get("code")
        ok = got == want and got_code == want_code
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:14} -> {got} {got_code or ''}  ({(r.get('meta') or {}).get('retrieval_method', '')})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
