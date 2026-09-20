"""Deterministic tests for every reason the agent hands a conversation to a
person. No Ollama, no OpenSearch: a scripted FakeAgent stands in for the model
and retrieval is pinned to the keyword scorer, so these run anywhere.

    .venv/bin/python -m tests.test_escalation      # or: pytest tests/
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.layer1 import opensearch_retrieval
from src.layer1.catalog import manual_for
from src.layer1.registration import load_registrations
from src.layer1.retrieval import keyword_retrieve, load_sections
from src.layer2 import agent as A
from src.layer3b import tickets


class FakeAgent:
    """Answers PHRASE_STEP_PROMPT with the raw step and OUTCOME_PROMPT from a script."""

    def __init__(self, outcomes=()):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, prompt):
        self.calls += 1
        if prompt.startswith("A customer was asked to try"):
            return self.outcomes.pop(0)
        return "STEP: " + prompt.split('taken directly from the manual: "')[1].split('"')[0]


def _setup():
    from src.storage import get_store
    get_store().ticket_dir = Path(tempfile.mkdtemp())
    opensearch_retrieval.retrieve = lambda q, p: (*keyword_retrieve(q, load_sections(p)), "keyword_fallback")
    return {(r.customer_name, r.product_id): r for r in load_registrations()}


REGS = _setup()
PRIYA_FC = REGS[("Priya Sharma", "WM-FC-700")]
RAVI_AC = REGS[("Ravi Kumar", "AC-CB-15T")]
SAMEER_AC = REGS[("Sameer Khan", "AC-CB-15T")]


def test_matched_complaints_are_not_unmatched():
    for reg, text in [
        (PRIYA_FC, "My washing machine bangs loudly when it spins"),
        (PRIYA_FC, "my clothes smell bad after washing"),
        (RAVI_AC, "AC isn't cooling properly anymore"),
    ]:
        conv = A.start(reg, text, agent=FakeAgent())
        assert conv.ticket is None and conv.turns, f"should have offered a step: {text!r}"


def test_unmatched_escalates_instead_of_guessing():
    fake = FakeAgent()
    conv = A.start(PRIYA_FC, "The touch panel flickers and won't respond", agent=fake)
    assert conv.ticket and conv.ticket.reason_code == "unmatched"
    assert conv.turns == [] and fake.calls == 0, "must not call the model or offer a step"
    assert conv.section_heading == "" and "Closest section" in conv.escalation_detail


def test_recurring_issue_escalates_immediately():
    heading = "4.1 Not cooling properly / blowing warm or weak air"
    history = [A.PriorCase(RAVI_AC.serial_number, heading, datetime.now() - timedelta(days=21), "resolved")]
    conv = A.start(RAVI_AC, "the AC has stopped cooling again", agent=FakeAgent(), history=history)
    assert conv.ticket and conv.ticket.reason_code == "recurring"
    assert conv.turns == [] and "already handled" in conv.ticket.issue_summary


def test_recurrence_needs_same_product_same_section_and_recent():
    heading = "4.1 Not cooling properly / blowing warm or weak air"
    now = datetime.now()
    for label, case in {
        "other product": A.PriorCase(SAMEER_AC.serial_number, heading, now - timedelta(days=5), "resolved"),
        "other section": A.PriorCase(RAVI_AC.serial_number, "4.2 Foul or musty smell when the AC is running", now - timedelta(days=5), "resolved"),
        "too old": A.PriorCase(RAVI_AC.serial_number, heading, now - timedelta(days=A.RECURRENCE_DAYS + 30), "resolved"),
    }.items():
        conv = A.start(RAVI_AC, "AC not cooling", agent=FakeAgent(), history=[case])
        assert conv.ticket is None, f"{label} must not count as recurring"


def test_two_failed_steps_escalate():
    fake = FakeAgent(outcomes=["STILL_BROKEN", "STILL_BROKEN"])
    conv = A.start(RAVI_AC, "AC not cooling at all", agent=fake)
    conv = A.respond(conv, "cleaned the filters, still warm", agent=fake)
    assert conv.ticket is None and len(conv.turns) == 2
    conv = A.respond(conv, "checked the outdoor unit, still warm", agent=fake)
    assert conv.ticket and conv.ticket.reason_code == "attempts_exhausted"
    assert len(conv.ticket.attempts_tried) == 2


def test_resolved_creates_no_ticket():
    fake = FakeAgent(outcomes=["RESOLVED"])
    conv = A.start(PRIYA_FC, "washing machine banging on spin", agent=fake)
    conv = A.respond(conv, "levelled it, quiet now", agent=fake)
    assert conv.resolved and conv.ticket is None


def test_safety_skips_troubleshooting_and_quotes_the_manual():
    fake = FakeAgent()
    conv = A.start(SAMEER_AC, "there's a burning smell from the AC", agent=fake)
    assert conv.ticket.reason_code == "safety" and conv.safety_flag
    assert conv.turns == [] and fake.calls == 0
    assert "Stop use immediately" in conv.section_body, "manual's own instruction must be surfaced"


def test_every_code_has_a_label():
    for code in ("safety", "attempts_exhausted", "no_more_steps", "no_steps", "unmatched", "recurring"):
        assert code in A.ESCALATION_LABELS


def test_each_model_call_gets_a_fresh_agent():
    """A shared Strands Agent replays every earlier prompt as context (cross-customer bleed)."""
    made = []

    class Spy:
        def __init__(self, **kw): made.append(self); self.kw = kw
        def __call__(self, prompt): return "ok"

    real = A.Agent
    A.Agent = Spy
    try:
        sa = A.StatelessAgent.__new__(A.StatelessAgent)
        sa._model, sa.model_ms = object(), []
        sa("one"); sa("two")
    finally:
        A.Agent = real
    assert len(made) == 2 and made[0] is not made[1]
    assert made[0].kw["hooks"], "latency hook is attached"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
