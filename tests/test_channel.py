"""The WhatsApp channel end to end, minus the model and OpenSearch (stubbed): orders in -> registration
messages -> customer conversations -> hand-over -> a person replies. File store as the test double."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["AFTERCARE_STORE"] = "file"

from src.channel import bot
from src.domain import opensearch_retrieval
from src.domain.registration import FIXTURES
from src.domain.retrieval import keyword_retrieve, load_sections
from src.records import case_index
from src.storage import get_store
from src.webapp import api_core as core

store = get_store()
tmp = Path(tempfile.mkdtemp())
store.conv_dir, store.ticket_dir = tmp / "c", tmp / "t"
opensearch_retrieval.retrieve = lambda q, p: (*keyword_retrieve(q, load_sections(p)), "test_double")
case_index.prior_cases = lambda serial, days: []
case_index.record = lambda *a, **k: None
case_index.reset = lambda: None


class Stub:
    def __call__(self, prompt):
        if prompt.startswith("A customer was asked to try"):
            return "STILL_BROKEN"
        return "STEP: " + prompt.split('taken directly from the product manual: "')[1].split('"')[0]


core._agent = Stub()
ORDERS = (FIXTURES / "sandbox" / "orders_croma_sep2026.csv").read_text()
AQUA, ARCTIC = "aquaspin", "arcticair"


def say(brand, phone, text=None, button=None):
    inbound = {"type": "button", "id": button[0], "title": button[1]} if button else {"type": "text", "text": text}
    return bot.handle_inbound(brand, phone, inbound)


def chat(brand, phone):
    return store.chat_messages(brand, phone)


def test_orders_are_registered_and_each_customer_is_messaged():
    out, status = core.ingest_commit(ORDERS, source="sandbox")
    assert status == 200 and out["registered"] == 9 and out["rejected"] == 2, out
    assert {b["brand"]: b["products"] for b in out["brands"]} == {"AquaSpin": 6, "ArcticAir": 3}
    assert any("TV-55-X" in i["problem"] for i in out["issues"]) and any("Phone is not" in i["problem"] for i in out["issues"])
    first = chat(AQUA, "+919000000101")[0]
    assert first["sender"] == "aftercare" and "registered with AquaSpin" in first["text"] and "WM-FC-91011" in first["text"]
    assert "Motor warranty (2 years): active until" in first["text"]
    assert core.regs_for_phone("+919000000101")[0].customer_name == "Arjun Mehta"
    assert chat(ARCTIC, "+919000000101") == [], "another brand's line never sees this customer"


def test_a_customer_with_one_product_gets_a_step_then_a_resolution():
    phone = "+919000000101"
    out = say(AQUA, phone, "My washing machine bangs loudly when it spins")
    assert out[0]["sender"] == "aftercare" and out[0]["text"].startswith("STEP:")
    assert store.get_chat_state(AQUA, phone)["mode"] == "bot"
    core._agent = type("Y", (), {"__call__": lambda self, p: "STEP: x"})()      # rules decide a clear "fixed"
    out = say(AQUA, phone, "That fixed it, thank you!")
    assert any(m["kind"] == "note" and "Resolved" in m["text"] for m in out)
    assert store.get_chat_state(AQUA, phone)["mode"] == "idle"
    core._agent = Stub()


def test_two_products_means_the_customer_is_asked_which_and_can_tap_a_button():
    phone = "+919000000103"
    out = say(AQUA, phone, "My clothes smell bad after washing")
    assert out[0]["kind"] == "buttons" and len(out[0]["buttons"]) == 2
    assert store.get_chat_state(AQUA, phone)["mode"] == "awaiting_product"
    fc = next(b for b in out[0]["buttons"] if b["id"] == "prod:WM-FL-91014")
    out = say(AQUA, phone, button=(fc["id"], fc["title"]))
    assert out[0]["text"].startswith("STEP:"), out
    assert store.get_chat_state(AQUA, phone)["mode"] == "bot"


def test_naming_the_model_picks_the_product_without_asking():
    phone = "+919000000103"
    store.put_chat_state(AQUA, phone, {"mode": "idle"})
    out = say(AQUA, phone, "my FL-900 makes a banging noise")
    assert out[0]["kind"] == "text" and out[0]["text"].startswith("STEP:")


def test_warranty_question_is_answered_directly():
    phone = "+919000000104"
    out = say(AQUA, phone, "is my washing machine still under warranty?")
    assert out[0]["meta"]["status"] == "answered" and "5 Jun" not in out[0]["text"]
    assert "Motor (2 years): active until 01 Jul 2027" in out[0]["text"] and "Other parts (1 year): expired on 01 Jul 2026" in out[0]["text"]
    assert store.get_chat_state(AQUA, phone)["mode"] == "idle"


def test_handover_then_a_person_replies_and_resolves():
    phone = "+919000000108"
    out = say(AQUA, phone, "I want to talk to a real person")
    esc = out[0]["meta"]["escalation"]
    assert esc["code"] == "human_requested" and out[1]["kind"] == "note" and "Ticket TBB-" in out[1]["text"]
    state = store.get_chat_state(AQUA, phone)
    assert state["mode"] == "human"
    tid = state["ticket_id"]
    # the customer writes again: the bot stays out of it and acknowledges once
    ack = say(AQUA, phone, "hello? is anyone there")
    assert len(ack) == 1 and "added to your ticket" in ack[0]["text"]
    assert say(AQUA, phone, "please hurry") == []
    row = store.get_ticket(tid)
    idx = next(i for i in store.chat_index(AQUA) if i["phone"] == phone)
    assert idx["mode"] == "human" and idx["unread"] == 2
    # a person replies from the inbox: it lands in the same chat
    reply = bot.staff_reply(row, "Hi Meera, this is Dev from AquaSpin. How can I help?", "Dev Patel")
    assert chat(AQUA, phone)[-1]["sender"] == "human" and reply["meta"]["staff"] == "Dev Patel"
    bot.ticket_resolved(row, "Dev Patel")
    assert store.get_chat_state(AQUA, phone)["mode"] == "idle"


def test_a_number_that_never_bought_is_told_so():
    out = say(AQUA, "+919999999999", "hello")
    assert "can't find a purchase registered to this number" in out[0]["text"]


def test_meta_shaped_webhook_reaches_the_bot():
    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {
        "metadata": {"display_phone_number": "+91 1800 000 0002"},
        "messages": [{"from": "919000000107", "id": "wamid.1", "type": "text", "text": {"body": "There's a burning smell coming from my AC"}}]}}]}]}
    data, status = core.wa_webhook(payload)
    assert status == 200 and data["replies"][0]["meta"]["escalation"]["code"] == "safety"
    assert store.get_chat_state(ARCTIC, "+919000000107")["mode"] == "human"


def test_reset_clears_chats_and_sandbox_orders():
    core.sandbox_reset()
    assert core.regs_for_phone("+919000000101") == [] and chat(AQUA, "+919000000101") == []


if __name__ == "__main__":
    fails = 0
    for name, fn in [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]:
        try:
            fn(); print("PASS ", name)
        except AssertionError as e:
            fails += 1; print("FAIL ", name, e)
        except Exception as e:
            fails += 1; print("ERROR", name, type(e).__name__, e)
    print("all passed" if not fails else f"{fails} failed")
    sys.exit(1 if fails else 0)
