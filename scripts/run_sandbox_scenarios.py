"""Drive the sandbox the way the browser does (Meta-shaped webhook, polling, the staff endpoints) and check
each persona's story ends the way the runbook says. Real model, real services; takes a few minutes.

    .venv/bin/python scripts/run_sandbox_scenarios.py [http://127.0.0.1:3000] [-v]
"""
import sys

import requests

BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:3000").rstrip("/")
VERBOSE = "-v" in sys.argv
LINE = {"aquaspin": "+91 1800 000 0001", "arcticair": "+91 1800 000 0002"}
results = []


def post(path, **kw):
    return requests.post(BASE + path, timeout=300, **kw)


def say(brand, phone, text=None, button=None):
    digits = phone.lstrip("+")
    msg = {"from": digits, "id": "wamid.x", "timestamp": "1"}
    msg |= ({"type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": button[0], "title": button[1]}}} if button
            else {"type": "text", "text": {"body": text}})
    body = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {"metadata": {"display_phone_number": LINE[brand]}, "messages": [msg]}}]}]}
    r = post("/api/wa/webhook", json=body)
    r.raise_for_status()
    replies = r.json()["replies"]
    if VERBOSE:
        print(f"   customer: {text or button[1]}")
        for m in replies:
            print(f"   {m['sender']:9} [{m['kind']}] {m['text'][:150]!r}")
    return replies


def status(replies):
    return next((m["meta"]["status"] for m in replies if m.get("meta", {}).get("status")), "")


def code(replies):
    return next(((m["meta"].get("escalation") or {}).get("code") for m in replies if m.get("meta", {}).get("escalation")), None)


def check(name, cond, detail=""):
    results.append(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + ("" if cond else f"   {detail}"))


def main():
    post("/api/sandbox/reset")
    for f in ("orders_croma_sep2026.csv", "orders_aquaspin_direct.csv"):
        csv = requests.get(f"{BASE}/api/sandbox/samples/{f}").text
        out = post("/api/sandbox/ingest", data=csv, headers={"Content-Type": "text/csv"}).json()
        check(f"orders: {f}", out.get("registered", 0) >= 3, out)
    msgs = requests.get(f"{BASE}/api/wa/messages", params={"brand": "aquaspin", "phone": "+919000000101"}).json()["messages"]
    check("registration message delivered to Arjun", bool(msgs) and "registered with AquaSpin" in msgs[0]["text"], msgs)

    print("\n-- S1 Arjun: fixed in one step")
    r = say("aquaspin", "+919000000101", "My washing machine bangs loudly when it spins")
    check("  offered a step from 4.1", status(r) == "waiting" and "4.1" in r[1]["text"], r)
    r = say("aquaspin", "+919000000101", "That fixed it, thank you!")
    check("  resolved, no ticket", status(r) == "resolved", r)

    print("\n-- S2 Kavya: two steps, still broken")
    r = say("arcticair", "+919000000102", "My AC isn't cooling the room")
    check("  step 1 (4.1)", status(r) == "waiting" and "4.1" in r[1]["text"], r)
    r = say("arcticair", "+919000000102", "Still blowing warm air")
    check("  step 2", status(r) == "waiting", r)
    r = say("arcticair", "+919000000102", "No change, still not cooling")
    check("  handed over: two steps tried", code(r) == "attempts_exhausted", r)

    print("\n-- S3 Rohan: two products, then 'it's back'")
    r = say("aquaspin", "+919000000103", "Hi")
    check("  greeting with buttons", r[0]["kind"] == "buttons" and "Report a problem" in [b["title"] for b in r[0]["buttons"]], r)
    r = say("aquaspin", "+919000000103", "My clothes smell bad after washing")
    check("  asks which product", r[0]["kind"] == "buttons" and len(r[0]["buttons"]) == 2, r)
    fc = next(b for b in r[0]["buttons"] if b["id"].endswith("WM-FC-91013"))
    r = say("aquaspin", "+919000000103", button=(fc["id"], fc["title"]))
    check("  recurring problem handed over", code(r) == "recurring", r)

    print("\n-- S4 Neha: warranty check (parts expired, motor active)")
    r = say("aquaspin", "+919000000104", "Is my machine still under warranty?")
    t = r[0]["text"]
    check("  answered from dates", status(r) == "answered" and "active until 01 Jul 2027" in t and "expired on 01 Jul 2026" in t, t)

    print("\n-- S5 Imran: compressor warranty, then a leak")
    r = say("arcticair", "+919000000105", "Is my AC compressor covered under warranty?")
    check("  compressor active, parts expired", status(r) == "answered" and "active until 10 Aug 2027" in r[0]["text"], r[0]["text"])
    r = say("arcticair", "+919000000105", "Water is dripping from my AC")
    check("  step from 4.3", status(r) == "waiting" and "4.3" in r[1]["text"], r)

    print("\n-- S6 Divya: out of warranty, then something not in the manual")
    r = say("aquaspin", "+919000000106", "is my washing machine under warranty?")
    check("  both expired", status(r) == "answered" and r[0]["text"].count("expired on") == 2, r[0]["text"])
    r = say("aquaspin", "+919000000106", "The touch panel flickers and won't respond")
    check("  not in the manual, handed over", code(r) == "unmatched", r)

    print("\n-- S7 Sanjay: safety")
    r = say("arcticair", "+919000000107", "There's a burning smell coming from my AC")
    check("  safety, manual's warning", code(r) == "safety" and "Stop use immediately" in r[0]["text"], r)

    print("\n-- S8 Meera: asks for a person; the brand replies from its inbox")
    r = say("aquaspin", "+919000000108", "I want to talk to a person")
    check("  human requested", code(r) == "human_requested", r)
    tid = next(m["meta"]["ticket_id"] for m in r if m.get("meta", {}).get("ticket_id"))
    s = requests.Session()
    s.post(BASE + "/api/login", json={"username": "dev.patel", "passcode": "aqua-agent"})
    inbox = s.get(f"{BASE}/api/inbox/aquaspin").json()["chats"]
    check("  appears first in the inbox, phone masked", inbox[0]["ticket_id"] == tid and "·" in inbox[0]["phone"], inbox[:1])
    rep = s.post(f"{BASE}/api/tickets/{tid}/reply", json={"text": "Hi Meera, this is Dev from AquaSpin. Which cycle is the machine on?"})
    check("  an agent may reply (Cedar)", rep.status_code == 200, rep.text)
    msgs = requests.get(f"{BASE}/api/wa/messages", params={"brand": "aquaspin", "phone": "+919000000108"}).json()["messages"]
    check("  the reply reached the customer's phone", msgs[-1]["sender"] == "human" and "Dev from AquaSpin" in msgs[-1]["text"], msgs[-1])
    check("  an agent may not resolve (Cedar)", s.post(f"{BASE}/api/tickets/{tid}/status", json={"status": "resolved"}).status_code == 403)
    m = requests.Session()
    m.post(BASE + "/api/login", json={"username": "meera.nair", "passcode": "aqua-manager"})
    check("  a manager may resolve", m.post(f"{BASE}/api/tickets/{tid}/status", json={"status": "resolved"}).status_code == 200)
    msgs = requests.get(f"{BASE}/api/wa/messages", params={"brand": "aquaspin", "phone": "+919000000108"}).json()["messages"]
    check("  the customer is told it was resolved", "marked resolved" in msgs[-1]["text"], msgs[-1])

    print("\n-- dashboard analytics reflect all of it")
    d = m.get(f"{BASE}/api/dashboard/aquaspin").json()["insights"]
    check("  insights: resolved, answered, escalated all counted", d["resolved"] >= 1 and d["answered"] >= 2 and d["escalated"] >= 3, d)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
