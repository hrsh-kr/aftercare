"""Record the sandbox's eight personas from a RUNNING local stack (bash scripts/dev.sh) into
public/static/recording.json, exactly as the browser would drive them: through the Meta-shaped webhook and the
staff endpoints. The deployed demo page plays this back. Nothing in the recording is written by hand; only the
persona blurbs and the choice of what each persona says are.

    .venv/bin/python scripts/record_playback.py [http://127.0.0.1:3000]
Then: .venv/bin/python scripts/build_site.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:3000").rstrip("/")
OUT = Path(__file__).resolve().parent.parent / "public" / "static" / "recording.json"
LINE = {"aquaspin": "+91 1800 000 0001", "arcticair": "+91 1800 000 0002"}
NAMES = {"aquaspin": "AquaSpin", "arcticair": "ArcticAir"}


def post(path, **kw):
    return requests.post(BASE + path, timeout=300, **kw)


def webhook(brand, phone, text=None, button=None):
    digits = phone.lstrip("+")
    msg = {"from": digits, "id": "wamid.rec", "timestamp": "1"}
    msg |= ({"type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": button["id"], "title": button["title"]}}} if button
            else {"type": "text", "text": {"body": text}})
    body = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {"metadata": {"display_phone_number": LINE[brand]}, "messages": [msg]}}]}]}
    r = post("/api/wa/webhook", json=body)
    r.raise_for_status()
    return r.json()["replies"]


def clean(m):
    """A message as the phone shows it (drop the storage cursor)."""
    return {k: v for k, v in m.items() if k != "cursor"}


class Persona:
    def __init__(self, pid, name, brand, phone, blurb, outcome):
        self.d = {"id": pid, "name": name, "brand": brand, "phone_masked": phone[:6] + " " + phone[6:9] + "·····", "blurb": blurb,
                  "outcome": outcome, "steps": []}
        self.phone, self.brand = phone, brand

    def registration(self):
        msgs = requests.get(f"{BASE}/api/wa/messages", params={"brand": self.brand, "phone": self.phone}).json()["messages"]
        self.d["registration"] = [clean(m) for m in msgs if (m.get("meta") or {}).get("kind") == "registration"][:2]
        return self

    def say(self, text=None, button_title=None):
        button = None
        if button_title:
            last = next(m for m in reversed(requests.get(f"{BASE}/api/wa/messages", params={"brand": self.brand, "phone": self.phone}).json()["messages"]) if m.get("kind") == "buttons")
            button = next(b for b in last["buttons"] if b["title"] == button_title)
        replies = webhook(self.brand, self.phone, text=text, button=button)
        self.d["steps"].append({"who": "customer", "text": text if text else button_title, "button": bool(button), "replies": [clean(m) for m in replies]})
        return replies


def main():
    print("reset + load the Croma order file")
    post("/api/sandbox/reset")
    csv = requests.get(f"{BASE}/api/sandbox/samples/orders_croma_sep2026.csv").text
    ingest = post("/api/sandbox/ingest", data=csv, headers={"Content-Type": "text/csv"}).json()

    P = []
    def new(*a):
        p = Persona(*a).registration()
        P.append(p)
        return p

    p = new("arjun", "Arjun Mehta", "aquaspin", "+919000000101", "A noisy washer. One step fixes it.", "Fixed, no ticket")
    p.say("My washing machine bangs loudly when it spins"); p.say("That fixed it, thank you!")

    p = new("kavya", "Kavya Nair", "arcticair", "+919000000102", "An AC that won't cool. Two steps, no luck.", "Handed to a person")
    p.say("My AC isn't cooling the room"); p.say("Still blowing warm air"); p.say("No change, still not cooling")

    p = new("rohan", "Rohan Desai", "aquaspin", "+919000000103", "Two machines. The smell is back.", "Recurring issue, spotted")
    p.say("Hi"); p.say("My clothes smell bad after washing"); p.say(button_title="FC-700 Washing Machine")

    p = new("neha", "Neha Kulkarni", "aquaspin", "+919000000104", "Is my warranty still on?", "Answered from the purchase date")
    p.say("Is my machine still under warranty?")

    p = new("imran", "Imran Sheikh", "arcticair", "+919000000105", "Compressor cover, then a leak.", "Answered, then a fix")
    p.say("Is my AC compressor covered under warranty?"); p.say("Water is dripping from my AC")

    p = new("divya", "Divya Rao", "aquaspin", "+919000000106", "A fault that isn't in the manual.", "Won't guess. Hands over")
    p.say("Is my machine still under warranty?"); p.say("The touch panel flickers and won't respond")

    p = new("sanjay", "Sanjay Iyer", "arcticair", "+919000000107", "A burning smell.", "Safety first. No troubleshooting")
    p.say("There's a burning smell coming from my AC")

    p = new("meera", "Meera Pillai", "aquaspin", "+919000000108", "“Let me talk to a person.”", "A person takes over")
    rep = p.say("I want to talk to a person")
    tid = next(m["meta"]["ticket_id"] for m in rep if (m.get("meta") or {}).get("ticket_id"))

    agent = requests.Session(); agent.post(BASE + "/api/login", json={"username": "dev.patel", "passcode": "aqua-agent"})
    manager = requests.Session(); manager.post(BASE + "/api/login", json={"username": "meera.nair", "passcode": "aqua-manager"})
    r = agent.post(f"{BASE}/api/tickets/{tid}/reply", json={"text": "Hi Meera, this is Dev from AquaSpin. Which cycle is the machine on?"})
    p.d["steps"].append({"who": "staff", "actor": "Dev Patel (agent)", "text": "Hi Meera, this is Dev from AquaSpin. Which cycle is the machine on?",
                         "result": f"Allowed by {', '.join(r.json()['decision']['policies'])}" if r.ok else r.json()["error"], "replies": []})
    r = agent.post(f"{BASE}/api/tickets/{tid}/status", json={"status": "resolved"})
    p.d["steps"].append({"who": "staff_action", "actor": "Dev Patel (agent)", "action": "Resolve ticket", "ok": r.ok, "result": r.json().get("error", ""), "replies": []})
    r = manager.post(f"{BASE}/api/tickets/{tid}/status", json={"status": "resolved"})
    msgs = requests.get(f"{BASE}/api/wa/messages", params={"brand": "aquaspin", "phone": p.phone}).json()["messages"]
    p.d["steps"].append({"who": "staff_action", "actor": "Meera Nair (manager)", "action": "Resolve ticket", "ok": r.ok,
                         "result": f"Allowed by {', '.join(r.json()['decision']['policies'])}" if r.ok else r.json().get("error", ""), "replies": [clean(msgs[-1])]})

    print("dashboard snapshots")
    dash = {"aquaspin": manager.get(f"{BASE}/api/dashboard/aquaspin").json()}
    denied = manager.get(f"{BASE}/api/dashboard/arcticair")
    dash["arcticair"] = {"_status": denied.status_code, **denied.json()}
    threads = {}
    for t in dash["aquaspin"]["tickets"]:
        threads[t["ticket_id"]] = manager.get(f"{BASE}/api/tickets/{t['ticket_id']}/thread").json()
    health = requests.get(BASE + "/api/health").json()

    rec = {
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "model": "gemma2:9b",
        "stack": {k: ("ok" if v["ok"] else "down") for k, v in health["components"].items()},
        "ingest": ingest, "personas": [x.d for x in P], "dashboard": dash, "threads": threads,
        "health": health, "csv": {"clean": requests.get(BASE + "/api/sample-csv").text},
    }
    messy = ("customer_name,customer_phone,product_id,product_name,serial_number,purchase_date,retailer,purchase_price\n"
             "Asha Rao,+919800000001,WM-FC-700,AquaSpin FC-700 Washing Machine,WM-FC-80001,2026-02-11,Reliance Digital,25999\n"
             "Karan Shah,+919800000002,AC-CB-15T,ArcticAir 1.5T Split AC,AC-CB-80002,2026-03-02,Reliance Digital,33999\n"
             "Meena Iyer,+919800000003,TV-55-X,Mystery 55in TV,TV-80003,2026-03-09,Reliance Digital,45999\n"
             "Rohit Jain,+919800000004,AC-CB-15T,ArcticAir 1.5T Split AC,AC-CB-80002,2026-03-10,Reliance Digital,33999\n"
             "Sana Ali,98000,WM-FL-900,AquaSpin FL-900 Front Loader,WM-FL-80005,12/03/2026,Reliance Digital,35999")
    hdr = {"Content-Type": "text/csv"}
    rec["ingest_check"] = {"clean": requests.post(BASE + "/api/ingest", data=rec["csv"]["clean"], headers=hdr).json(),
                           "messy": requests.post(BASE + "/api/ingest", data=messy, headers=hdr).json()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1000} KB): {len(P)} personas, {sum(len(x.d['steps']) for x in P)} steps, {len(threads)} ticket threads")
    post("/api/sandbox/reset")


if __name__ == "__main__":
    main()
