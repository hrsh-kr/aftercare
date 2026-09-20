"""Does a customer's wording land on the right thing? No model involved (a stub words the steps), real
OpenSearch retrieval, so this checks retrieval, the gates and the intents.

    PYTHONPATH=. .venv/bin/python scripts/eval_routing.py

expect: "4.1" (offered a step from that manual section) | "unmatched" | "safety" | "human" | "warranty"
"""
import os

os.environ["AFTERCARE_STORE"] = "file"
import tempfile
from pathlib import Path

from src.agent import agent as A
from src.domain.registration import load_registrations
from src.storage import get_store

get_store().ticket_dir = Path(tempfile.mkdtemp())
get_store().conv_dir = Path(tempfile.mkdtemp())
REG = {(r.customer_name, r.product_id): r for r in load_registrations()}
WM = REG[("Priya Sharma", "WM-FC-700")]
AC = REG[("Ravi Kumar", "AC-CB-15T")]


class Stub:
    def __call__(self, prompt):
        return "STEP"


CASES = [
    (WM, "My washing machine bangs loudly when it spins", "4.1"), (WM, "the drum is shaking a lot during the spin cycle", "4.1"),
    (WM, "washing machine makes a loud banging noise", "4.1"), (WM, "my clothes smell bad after washing", "4.2"),
    (WM, "there is a musty smell from the drum", "4.2"), (WM, "dirty residue on my clothes after wash", "4.2"),
    (WM, "washing machine won't turn on", "4.3"), (WM, "machine has no power and does not start", "4.3"),
    (WM, "water is not draining from the washing machine", "4.5"), (WM, "the machine shows error E4", "4.5"),
    (WM, "I can't open the door after the wash", "4.6"), (WM, "door is stuck locked after cycle", "4.6"),
    (WM, "there is a burning smell coming from my machine", "safety"), (WM, "I see sparks near the plug", "safety"),
    (WM, "water is leaking all over the floor from the machine", "safety"),
    (WM, "The touch panel flickers and won't respond", "unmatched"), (WM, "my machine plays the wrong ringtone", "unmatched"),
    (WM, "is my washing machine still under warranty?", "warranty"), (WM, "what does the warranty cover", "warranty"),
    (WM, "when does my warranty expire", "warranty"),
    (WM, "I want to talk to a real person", "human"), (WM, "connect me to a human agent", "human"),
    (AC, "My AC is on but the room isn't cooling", "4.1"), (AC, "AC blowing warm air", "4.1"),
    (AC, "weak airflow and the AC is not cold", "4.1"), (AC, "my AC smells musty", "4.2"),
    (AC, "bad smell when the AC runs", "4.2"), (AC, "water dripping from the indoor unit of my AC", "4.3"),
    (AC, "AC is leaking water inside", "4.3"), (AC, "my AC remote is not working", "4.5"),
    (AC, "remote does not respond to buttons", "4.5"), (AC, "AC makes a rattling noise", "4.6"),
    (AC, "loud noise from the outdoor unit", "4.6"), (AC, "There's a burning smell coming from my AC", "safety"),
    (AC, "the AC is sparking", "safety"), (AC, "there is smoke from the outdoor unit", "safety"),
    (AC, "Wi-Fi app keeps disconnecting from my AC", "unmatched"),
    (AC, "is my AC compressor covered under warranty", "warranty"), (AC, "how long is the warranty on my AC", "warranty"),
    (AC, "please have someone call me", "human"), (AC, "I need to speak to a person", "human"),
]


def outcome(conv) -> str:
    if conv.escalation_code == "safety":
        return "safety"
    if conv.escalation_code == "unmatched":
        return "unmatched"
    if conv.escalation_code == "human_requested":
        return "human"
    if conv.answered:
        return "warranty"
    if conv.turns:
        return conv.section_heading.split()[0]
    return f"escalated:{conv.escalation_code}"


if __name__ == "__main__":
    bad = 0
    for reg, text, want in CASES:
        conv = A.start(reg, text, agent=Stub())
        got = outcome(conv)
        ok = got == want
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {reg.product_id[:2]}  {text[:58]:58} -> {got}" + ("" if ok else f"   (wanted {want}; section {conv.section_heading[:40]!r})"))
    print(f"\n{len(CASES) - bad}/{len(CASES)} routed as intended")
