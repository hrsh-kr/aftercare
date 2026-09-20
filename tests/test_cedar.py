"""Authorization: Cedar policy matrix + the server-side session.
Uses the real Cedar CLI (tools/cedar/cedar). Run: .venv/bin/python -m tests.test_cedar"""
import os
import sys
import tempfile

os.environ["AFTERCARE_STORE"] = "file"   # unit-test double; the app itself runs on DynamoDB
from pathlib import Path

from src.authz import cedar_authz, session
from src.layer3b import tickets
from src.webapp import api_core as core
from tests.lambda_client import Client

MANAGER = {"id": "m", "brand": "aquaspin", "role": "manager"}
AGENT = {"id": "a", "brand": "aquaspin", "role": "agent"}


def test_policies_typecheck_against_schema():
    ok, msg = cedar_authz.validate()
    assert ok, msg


def test_matrix():
    A = cedar_authz.authorize
    # (principal, action, resource type, brand, safety, expected allow, deciding policy)
    rows = [
        (AGENT, "viewDashboard", "Brand", "aquaspin", False, True, "same-brand-views-dashboard"),
        (AGENT, "viewDashboard", "Brand", "arcticair", False, False, "no-cross-brand"),
        (MANAGER, "viewDashboard", "Brand", "arcticair", False, False, "no-cross-brand"),
        (AGENT, "viewTicket", "Ticket", "aquaspin", False, True, "same-brand-views-ticket"),
        (AGENT, "updateTicketStatus", "Ticket", "aquaspin", False, False, None),   # agents may not
        (MANAGER, "updateTicketStatus", "Ticket", "aquaspin", False, True, "managers-update-ticket-status"),
        (MANAGER, "updateTicketStatus", "Ticket", "arcticair", False, False, "no-cross-brand"),
        (AGENT, "replyToCustomer", "Ticket", "aquaspin", False, True, "same-brand-staff-reply"),
        (MANAGER, "replyToCustomer", "Ticket", "arcticair", False, False, "no-cross-brand"),
        (AGENT, "viewPhoneUnmasked", "Ticket", "aquaspin", False, False, None),    # masked unless safety
        (AGENT, "viewPhoneUnmasked", "Ticket", "aquaspin", True, True, "safety-tickets-show-phone"),
        (AGENT, "viewPhoneUnmasked", "Ticket", "arcticair", True, False, "no-cross-brand"),
    ]
    for p, action, rtype, brand, safety, want, policy in rows:
        attrs = {"brand": brand} if rtype == "Brand" else {"brand": brand, "safety": safety}
        d = A(p, action, rtype, "x", attrs)
        assert d.allowed == want, (p["role"], action, brand, safety, d)
        if policy:
            assert policy in d.policies, (action, brand, d)


def test_session_is_server_side():
    assert session.authenticate("dev.patel", "wrong") is None
    assert session.authenticate("nobody", "x") is None
    p = session.authenticate("dev.patel", "aqua-agent")
    token = session.issue(p)
    assert session.verify(token) == p
    assert session.verify(token[:-2] + "xx") is None, "tampered token"
    assert session.verify("aquaspin") is None, "a bare brand name is not a session"


def test_http_forged_header_is_ignored_and_cross_brand_denied():
    c = Client()
    assert c.get("/api/dashboard/aquaspin", headers={"X-Staff-Brand": "aquaspin"}).status_code == 401
    assert c.post("/api/login", json={"username": "dev.patel", "passcode": "nope"}).status_code == 401
    r = c.post("/api/login", json={"username": "dev.patel", "passcode": "aqua-agent"})
    assert r.status_code == 200 and "token" not in r.json
    assert "HttpOnly" in r.headers["Set-Cookie"]
    assert c.get("/api/dashboard/aquaspin").status_code == 200
    r = c.get("/api/dashboard/arcticair", headers={"X-Staff-Brand": "arcticair"})   # forging the old header changes nothing
    assert r.status_code == 403 and "no-cross-brand" in r.json["error"]


def test_only_managers_change_ticket_status():
    with tempfile.TemporaryDirectory() as d:
        from src.storage import get_store
        get_store().ticket_dir = Path(d)
        t = tickets.Ticket(ticket_id="TBB-9999", customer_name="X", customer_phone="+919876543210", product_name="P",
                           serial_number="S", issue_summary="i", product_id="WM-FC-700", reason_code="unmatched")
        t.save()
        agent, mgr = Client(), Client()
        agent.post("/api/login", json={"username": "dev.patel", "passcode": "aqua-agent"})
        mgr.post("/api/login", json={"username": "meera.nair", "passcode": "aqua-manager"})
        r = agent.post("/api/tickets/TBB-9999/status", json={"status": "resolved"})
        assert r.status_code == 403, r.json
        assert mgr.post("/api/tickets/TBB-9999/status", json={"status": "resolved"}).status_code == 200
        assert tickets.Ticket.load_all()[0].status == "resolved"
        row = mgr.get("/api/dashboard/aquaspin").json["tickets"][0]
        assert row["customer_phone"].endswith("·····") and not row["phone_unmasked"]


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        try:
            fn(); print("PASS ", name)
        except AssertionError as e:
            fails += 1; print("FAIL ", name, e)
    print("all passed" if not fails else f"{fails} failed")
    sys.exit(1 if fails else 0)
