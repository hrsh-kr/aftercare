"""One contract, both storage backends: whatever the file store does, DynamoDB must do the same.
DynamoDB Local must be up (scripts/start_dynamodb.sh); that half skips itself if it isn't.
Run: .venv/bin/python -m tests.test_store_contract"""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("AFTERCARE_STORE", "file")
from src.storage.file_store import FileStore


def contract(store, label):
    store.clear()
    # conversations round-trip whole
    store.put_conversation("c1", {"registration": {"serial_number": "S1", "product_id": "WM-FC-700"}, "x": [1, 2]})
    assert store.get_conversation("c1")["x"] == [1, 2], label
    assert store.get_conversation("nope") is None, label
    # ids are sequential and unique
    ids = [store.next_ticket_id() for _ in range(3)]
    if label == "dynamodb":
        assert ids == ["TBB-0001", "TBB-0002", "TBB-0003"], ids
    # tickets are brand-scoped and findable by id
    for i, (pid, brand) in enumerate((("WM-FC-700", "aquaspin"), ("AC-CB-15T", "arcticair"), ("WM-FC-700", "aquaspin"))):
        store.put_ticket(brand, {"ticket_id": f"TBB-{i+1:04d}", "product_id": pid, "status": "new", "attempts_tried": ["a"], "safety_flag": False})
    assert [t["ticket_id"] for t in store.tickets("aquaspin")] == ["TBB-0001", "TBB-0003"], label
    assert [t["ticket_id"] for t in store.tickets("arcticair")] == ["TBB-0002"], label
    assert store.get_ticket("TBB-0002")["product_id"] == "AC-CB-15T", label
    assert store.get_ticket("TBB-9999") is None, label
    store.put_ticket("aquaspin", {"ticket_id": "TBB-0001", "product_id": "WM-FC-700", "status": "resolved", "attempts_tried": [], "safety_flag": False})
    assert store.get_ticket("TBB-0001")["status"] == "resolved", f"{label}: update overwrites"
    assert len(store.tickets("aquaspin")) == 2, f"{label}: no duplicate on update"
    return store


def cases_contract(store, label):
    """Cases: FileStore derives them from conversations; DynamoDB stores them. Same answers."""
    now = datetime.now()
    def conv(cid, days_ago, resolved=True):
        return {"registration": {"serial_number": "S1", "product_id": "WM-FC-700"}, "resolved": resolved, "ticket": None if resolved else {"x": 1},
                "source": "manual", "section_heading": "4.1", "safety_flag": False, "escalation_code": "" if resolved else "unmatched",
                "created_at": (now - timedelta(days=days_ago)).isoformat()}
    for cid, d, res in (("old", 200, True), ("new", 3, True), ("esc", 1, False)):
        store.put_conversation(cid, conv(cid, d, res))
        c = conv(cid, d, res)
        store.put_case("aquaspin", {"conversation_id": cid, "brand": "aquaspin", "serial_number": "S1", "product_id": "WM-FC-700",
                                    "section_heading": "4.1", "source": "manual", "outcome": "resolved" if res else "escalated",
                                    "reason_code": c["escalation_code"], "created_at": c["created_at"]})
    since = (now - timedelta(days=90)).isoformat()
    assert sorted(c["conversation_id"] for c in store.cases_for_serial("S1", since)) == ["esc", "new"], label
    assert len(store.cases_for_brand("aquaspin")) == 3, label
    assert store.cases_for_brand("arcticair") == [], label


def registry_and_chat_contract(store, label):
    row = lambda serial, phone, pid, src: {"customer_name": "X", "customer_phone": phone, "product_id": pid, "product_name": "P",
                                          "serial_number": serial, "purchase_date": "2026-01-01", "retailer": "R", "purchase_price": 100, "source": src}
    store.put_registration(row("WM-FC-1", "+911", "WM-FC-700", "sandbox"))
    store.put_registration(row("WM-FL-2", "+911", "WM-FL-900", "baseline"))
    store.put_registration(row("AC-CB-3", "+912", "AC-CB-15T", "sandbox"))
    assert [r["serial_number"] for r in store.registrations_for_phone("+911")] == ["WM-FC-1", "WM-FL-2"], label
    assert [r["serial_number"] for r in store.registrations("aquaspin")] == ["WM-FC-1", "WM-FL-2"], label
    assert store.registrations_for_phone("+911")[0]["purchase_price"] == 100 and isinstance(store.registrations_for_phone("+911")[0]["purchase_price"], int), label
    assert store.delete_registrations("sandbox") == 2 and [r["serial_number"] for r in store.registrations("aquaspin")] == ["WM-FL-2"], label
    # chat log: ordered, resumable from a cursor, isolated per brand line + phone
    c1 = store.put_chat_message("aquaspin", "+911", {"sender": "customer", "kind": "text", "text": "hi", "meta": {"ms": 5}})
    store.put_chat_message("aquaspin", "+911", {"sender": "aftercare", "kind": "text", "text": "hello"})
    store.put_chat_message("arcticair", "+911", {"sender": "customer", "kind": "text", "text": "other line"})
    msgs = store.chat_messages("aquaspin", "+911")
    assert [m["text"] for m in msgs] == ["hi", "hello"] and msgs[0]["meta"]["ms"] == 5, label
    assert [m["text"] for m in store.chat_messages("aquaspin", "+911", after=msgs[0]["cursor"])] == ["hello"], label
    assert store.get_chat_state("aquaspin", "+911") in ({}, None), label
    store.put_chat_state("aquaspin", "+911", {"mode": "bot", "conversation_id": "c9"})
    assert store.get_chat_state("aquaspin", "+911")["conversation_id"] == "c9", label
    store.put_chat_index("aquaspin", "+911", {"phone": "+911", "customer_name": "X", "mode": "human", "updated_at": "2026-01-02"})
    store.put_chat_index("aquaspin", "+912", {"phone": "+912", "customer_name": "Y", "mode": "idle", "updated_at": "2026-01-03"})
    assert [c["phone"] for c in store.chat_index("aquaspin")] == ["+912", "+911"], label
    store.clear()
    assert store.chat_messages("aquaspin", "+911") == [] and store.chat_index("aquaspin") == [], f"{label}: clear() removes runtime data"
    assert [r["serial_number"] for r in store.registrations("aquaspin")] == ["WM-FL-2"], f"{label}: ...but keeps the registry"


def main() -> int:
    fs = FileStore()
    tmp = Path(tempfile.mkdtemp())
    fs.conv_dir, fs.ticket_dir = tmp / "c", tmp / "t"
    contract(fs, "file"); cases_contract(fs, "file"); registry_and_chat_contract(fs, "file")
    print("PASS  file store contract")
    os.environ["DYNAMODB_ENDPOINT"] = "http://localhost:8000"
    try:
        import boto3
        import src.storage.dynamodb_store as d
        from scripts.bootstrap_local import tables_from_template
        d.ENDPOINT, d.TABLE = "http://localhost:8000", "AftercareContractTest"   # never the app's own table
        client = boto3.client("dynamodb", endpoint_url=d.ENDPOINT, region_name="ap-south-1", aws_access_key_id="x", aws_secret_access_key="x")
        if d.TABLE not in client.list_tables()["TableNames"]:
            props = tables_from_template()["AftercareTable"]
            client.create_table(TableName=d.TABLE, **{k: props[k] for k in ("BillingMode", "AttributeDefinitions", "KeySchema", "GlobalSecondaryIndexes")})
        ds = d.DynamoStore()
        ds._table.load()
    except Exception as exc:
        print(f"SKIP  dynamodb store (DynamoDB Local not reachable: {str(exc)[:60]})")
        return 0
    contract(ds, "dynamodb"); cases_contract(ds, "dynamodb"); registry_and_chat_contract(ds, "dynamodb")
    ds.clear(); ds.delete_registrations("baseline")
    print("PASS  dynamodb store contract (same assertions, atomic ids)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
