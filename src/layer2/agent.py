"""Layer 2 -- the support agent. A real multi-turn loop: one step,
wait for the customer's reply, offer a second step or escalate based
on what actually happened. Capped at 2 self-service attempts.

Per DESIGN.md's honesty rules: never guess on safety, never invent a
fix the manual doesn't support, escalate rather than keep guessing.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from strands import Agent
from strands.models.ollama import OllamaModel

from src.layer1.registration import Registration
from src.layer1.retrieval import keyword_retrieve, load_sections
from src.layer3b.tickets import Ticket, next_ticket_id

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures"
MANUAL_BY_PREFIX = {
    "WM-": FIXTURES / "manual_windmere_washing_machine.md",
    "AC-": FIXTURES / "manual_windmere_ac.md",
}
TERMS_PATH = FIXTURES / "terms_windmere.md"
SAFETY_KEYWORDS = ["burning smell", "burning", "spark", "sparking", "smoke", "exposed wire", "shock", "gas smell"]
COVERAGE_KEYWORDS = ["warranty", "covered", "coverage", "expire", "claim", "under warranty"]
MAX_ATTEMPTS = 2


@dataclass
class Turn:
    attempt_number: int
    step: str
    customer_reply: str | None = None
    outcome: str | None = None  # resolved / still_broken / escalated


@dataclass
class Conversation:
    registration: Registration
    complaint: str
    source: str  # "manual" or "terms"
    section_heading: str
    section_body: str
    available_steps: list[str] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    safety_flag: bool = False
    resolved: bool = False
    ticket: Ticket | None = None


def _parse_numbered_steps(body: str, limit: int = MAX_ATTEMPTS) -> list[str]:
    """The manuals write troubleshooting as an explicit numbered list --
    use that structure directly instead of asking the model whether a
    next step exists. Same lesson as the warranty-date bug: don't let
    the model judge something the document already states outright."""
    matches = re.findall(r"^\d+\.\s+\*?\*?(.+)", body, flags=re.MULTILINE)
    return [m.strip() for m in matches[:limit]]


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    return Agent(model=OllamaModel(host="http://localhost:11434", model_id=model_id), callback_handler=None)


def _check_safety(complaint: str) -> bool:
    lower = complaint.lower()
    return any(kw in lower for kw in SAFETY_KEYWORDS)


def _is_coverage_question(complaint: str) -> bool:
    lower = complaint.lower()
    return any(kw in lower for kw in COVERAGE_KEYWORDS)


def _manual_for(product_id: str) -> Path:
    for prefix, path in MANUAL_BY_PREFIX.items():
        if product_id.startswith(prefix):
            return path
    raise ValueError(f"No manual mapped for product_id {product_id}")


PHRASE_STEP_PROMPT = """A customer's complaint: "{complaint}"

The one step to give them, taken directly from the manual: "{raw_step}"

Phrase this as one short, friendly message asking them to try it and report back. \
Don't add anything the raw step doesn't say, don't add extra steps. \
Answer with only the message, nothing else."""

OUTCOME_PROMPT = """A customer was asked to try: "{step}"

They replied: "{reply}"

Did this resolve their issue? Answer with only one word: RESOLVED or STILL_BROKEN."""


def start(registration: Registration, complaint: str, agent: Agent | None = None) -> Conversation:
    agent = agent or _build_agent()

    if _check_safety(complaint):
        conv = Conversation(registration=registration, complaint=complaint, source="manual", section_heading="", section_body="", safety_flag=True)
        conv.ticket = _escalate(conv, reason="Safety-flagged complaint -- no troubleshooting attempted.")
        return conv

    if _is_coverage_question(complaint):
        sections = load_sections(TERMS_PATH)
        source = "terms"
    else:
        sections = load_sections(_manual_for(registration.product_id))
        source = "manual"

    heading, body = keyword_retrieve(complaint, sections)
    available_steps = _parse_numbered_steps(body)
    conv = Conversation(
        registration=registration, complaint=complaint, source=source,
        section_heading=heading, section_body=body, available_steps=available_steps,
    )

    if not available_steps:
        # Nothing in this section is a self-service step (e.g. it's a
        # pure "this needs a technician" section) -- escalate directly
        # rather than inventing a step that isn't there.
        conv.ticket = _escalate(conv, reason="No self-service step found in the relevant section.")
        return conv

    phrased = str(agent(PHRASE_STEP_PROMPT.format(complaint=complaint, raw_step=available_steps[0]))).strip()
    conv.turns.append(Turn(attempt_number=1, step=phrased))
    return conv


def respond(conv: Conversation, customer_reply: str, agent: Agent | None = None) -> Conversation:
    """Feed the customer's reply to the most recent step. Mutates and
    returns the same Conversation -- decides resolved / next step /
    escalate.

    Which step comes next, and whether one exists at all, is read
    directly from conv.available_steps (parsed deterministically in
    start()) -- not decided by the model. See _parse_numbered_steps."""
    agent = agent or _build_agent()
    current = conv.turns[-1]
    current.customer_reply = customer_reply

    outcome = str(agent(OUTCOME_PROMPT.format(step=current.step, reply=customer_reply))).strip().upper()
    if "RESOLVED" in outcome and "STILL" not in outcome:
        current.outcome = "resolved"
        conv.resolved = True
        return conv

    current.outcome = "still_broken"

    next_index = current.attempt_number  # 0-indexed available_steps, 1-indexed attempt_number
    if current.attempt_number >= MAX_ATTEMPTS or next_index >= len(conv.available_steps):
        reason = (
            f"{MAX_ATTEMPTS} self-service attempts tried, issue persists."
            if current.attempt_number >= MAX_ATTEMPTS
            else "No further self-service step in the manual; needs a technician."
        )
        conv.ticket = _escalate(conv, reason=reason)
        return conv

    raw_step = conv.available_steps[next_index]
    phrased = str(agent(PHRASE_STEP_PROMPT.format(complaint=conv.complaint, raw_step=raw_step))).strip()
    conv.turns.append(Turn(attempt_number=current.attempt_number + 1, step=phrased))
    return conv


def _escalate(conv: Conversation, reason: str) -> Ticket:
    attempts = [t.step for t in conv.turns]
    ticket = Ticket(
        ticket_id=next_ticket_id(),
        customer_name=conv.registration.customer_name,
        customer_phone=conv.registration.customer_phone,
        product_name=conv.registration.product_name,
        serial_number=conv.registration.serial_number,
        issue_summary=f"{conv.complaint} -- {reason}",
        attempts_tried=attempts,
        safety_flag=conv.safety_flag,
    )
    ticket.save()
    return ticket
