"""Layer 2 -- the support agent. A real multi-turn loop: one step,
wait for the customer's reply, offer a second step or escalate based
on what actually happened. Capped at 2 self-service attempts.

Per DESIGN.md's honesty rules: never guess on safety, never invent a
fix the manual doesn't support, escalate rather than keep guessing.
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import time

from strands import Agent
from strands.hooks import AfterModelCallEvent, BeforeModelCallEvent, HookProvider, HookRegistry
from strands.models.ollama import OllamaModel

from src.errors import DependencyUnavailable
from src.layer1 import opensearch_retrieval
from src.layer1.catalog import BRAND_SLUGS, brand_for, manual_for, terms_for
from src.layer1.registration import Registration
from src.layer1.retrieval import content_words, load_sections
from src.layer3b.tickets import Ticket, next_ticket_id

# Overridable so a Lambda running inside SAM Local's Docker container can
# reach the host machine's Ollama server -- "localhost" inside that
# container means the container itself, not the host. The SAM template
# sets this to http://host.docker.internal:11434 for exactly this reason.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

SAFETY_KEYWORDS = ["burning smell", "burning", "burnt", "spark", "sparking", "smoke", "exposed wire", "shock", "gas smell",
                   "fumes", "melting", "short circuit", "electric"]
COVERAGE_KEYWORDS = ["warranty", "covered", "coverage", "expire", "claim", "under warranty"]
MAX_ATTEMPTS = 2
RECURRENCE_DAYS = 90

# Why a conversation went to a person. Every escalation carries exactly one of
# these codes (Ticket.reason_code) so the brand sees *why*, not just *that*.
ESCALATION_LABELS = {
    "safety": "Safety",
    "attempts_exhausted": "Two steps tried",
    "no_more_steps": "Manual has nothing more to try",
    "no_steps": "Needs a person",
    "unmatched": "Not in the manual",
    "recurring": "Recurring issue",
}

def diagnostic_overlap(complaint: str, heading: str, body: str) -> int:
    """How many meaningful words the complaint shares with the section the
    search returned. 0 means the manual doesn't address this -- and the
    honesty rule (DESIGN.md section 7) says escalate rather than guess."""
    return len(content_words(complaint) & content_words(f"{heading} {body}"))


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
    retrieval_method: str = ""  # "opensearch" or "keyword_fallback" -- see opensearch_retrieval.retrieve()
    escalation_code: str = ""   # one of ESCALATION_LABELS, set when a ticket is created
    escalation_detail: str = ""  # e.g. for "recurring": which earlier case matched
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PriorCase:
    """An earlier conversation about this exact product -- what the agent
    checks to recognise a recurring problem."""
    serial_number: str
    section_heading: str
    when: datetime
    outcome: str  # "resolved" | "escalated"


def _parse_numbered_steps(body: str, limit: int = MAX_ATTEMPTS) -> list[str]:
    """The manuals write troubleshooting as an explicit numbered list --
    use that structure directly instead of asking the model whether a
    next step exists. Same lesson as the warranty-date bug: don't let
    the model judge something the document already states outright."""
    matches = re.findall(r"^\d+\.\s+\*?\*?(.+)", body, flags=re.MULTILINE)
    return [m.strip() for m in matches[:limit]]


class _LatencyHook(HookProvider):
    """Strands hooks: time every model call. Read back into the response `meta` so the demo's
    trace can show what the model did and how long it took -- measured, not estimated."""

    def __init__(self, sink: list) -> None:
        self._sink = sink
        self._t0 = 0.0

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeModelCallEvent, self._before)
        registry.add_callback(AfterModelCallEvent, self._after)

    def _before(self, event: BeforeModelCallEvent) -> None:
        self._t0 = time.perf_counter()

    def _after(self, event: AfterModelCallEvent) -> None:
        self._sink.append(round((time.perf_counter() - self._t0) * 1000))


class StatelessAgent:
    """One fresh Strands Agent per call, sharing a single model client.

    Why not one long-lived Agent: a Strands Agent keeps every message it has seen and replays
    them as context. Shared across requests, that meant customer B's prompt was answered with
    customer A's complaint in its context (found by inspecting `agent.messages`: 4 messages
    after 2 calls), and the context grew without bound. Every prompt here is self-contained,
    so no call needs another's history."""

    def __init__(self, model_id: str = "qwen2.5-coder:7b") -> None:
        self._model = OllamaModel(host=OLLAMA_HOST, model_id=model_id)
        self.model_ms: list[int] = []

    def __call__(self, prompt: str):
        agent = Agent(model=self._model, callback_handler=None, hooks=[_LatencyHook(self.model_ms)])
        try:
            return agent(prompt)
        except Exception as exc:
            if isinstance(exc, (ConnectionError, OSError)) or "connect" in str(exc).lower():
                raise DependencyUnavailable("Ollama", str(exc)[:160]) from exc
            raise

    def drain_model_ms(self) -> list[int]:
        out, self.model_ms = self.model_ms, []
        return out


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> StatelessAgent:
    return StatelessAgent(model_id)


_NEGATORS = {"no", "not", "without", "never", "isnt", "doesnt", "dont", "cant", "nothing"}


def _check_safety(complaint: str) -> bool:
    """A safety keyword, unless it is plainly negated ("no burning smell", "without any smoke").

    The two ways to be wrong are not equal: a missed safety issue is far worse than an
    unneeded escalation. So negation only counts when the negator sits right before the
    keyword (within two words), and "not only ..." never counts ("not only a burning smell")."""
    text = " ".join(re.findall(r"[a-z]+", complaint.lower().replace("'", "")))
    for kw in SAFETY_KEYWORDS:
        for m in re.finditer(r"\b" + re.escape(kw), text):
            words = text[: m.start()].split()
            # "doesn't spark or smoke": the negation reaches across an "or"/"nor"
            before = words[-4:] if words[-1:] and words[-1] in ("or", "nor") else words[-2:]
            if not (set(before) & _NEGATORS) or "only" in before:
                return True
    return False


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


def _tidy(message: str, limit: int = 400) -> str:
    """Model output guard, applied before anything is stored: no emoji, no wrapping quotes,
    no runs of whitespace, bounded length. Customers see the same text the ticket records."""
    text = re.sub(r"\s+", " ", _EMOJI.sub("", message)).strip().strip('"').strip()
    return text[:limit].rstrip()


def _is_coverage_question(complaint: str) -> bool:
    lower = complaint.lower()
    return any(kw in lower for kw in COVERAGE_KEYWORDS)


PHRASE_STEP_PROMPT = """A customer's complaint: "{complaint}"

The one step to give them, taken directly from the manual: "{raw_step}"

Phrase this as one short, friendly message asking them to try it and report back. \
Don't add anything the raw step doesn't say, don't add extra steps. \
Answer with only the message, nothing else."""

OUTCOME_PROMPT = """A customer was asked to try: "{step}"

They replied: "{reply}"

Did this resolve their issue? Answer with only one word: RESOLVED or STILL_BROKEN."""


def _safety_instruction(product_id: str) -> tuple[str, str]:
    """The manual's own stop-use instruction (its burning/smoke section), shown
    to the customer verbatim -- deterministic, no model, no retrieval."""
    for heading, body in load_sections(manual_for(product_id)):
        if any(k in heading.lower() for k in ("burning", "smoke", "spark")):
            m = re.search(r"\*\*(.+?)\*\*", body, flags=re.DOTALL)
            return heading, (m.group(1) if m else body.splitlines()[0]).strip()
    return "", ""


def _find_recurrence(history: list[PriorCase] | None, registration: Registration, heading: str) -> PriorCase | None:
    """Same product, same manual section, already handled within the window."""
    cutoff = datetime.now() - timedelta(days=RECURRENCE_DAYS)
    matches = [
        c for c in (history or [])
        if c.serial_number == registration.serial_number and c.section_heading == heading and c.when >= cutoff
    ]
    return max(matches, key=lambda c: c.when) if matches else None


def start(registration: Registration, complaint: str, agent: Agent | None = None, history: list[PriorCase] | None = None) -> Conversation:
    agent = agent or _build_agent()

    if _check_safety(complaint):
        heading, instruction = _safety_instruction(registration.product_id)
        conv = Conversation(
            registration=registration, complaint=complaint, source="manual",
            section_heading=heading, section_body=instruction, safety_flag=True,
            retrieval_method="safety_rule",
        )
        conv.ticket = _escalate(conv, "safety", "Safety-flagged complaint -- no troubleshooting attempted.")
        return conv

    if _is_coverage_question(complaint):
        doc_path = terms_for(registration.product_id)
        source = "terms"
    else:
        doc_path = manual_for(registration.product_id)
        source = "manual"

    heading, body, retrieval_method = opensearch_retrieval.retrieve(complaint, doc_path)
    available_steps = _parse_numbered_steps(body)
    conv = Conversation(
        registration=registration, complaint=complaint, source=source,
        section_heading=heading, section_body=body, available_steps=available_steps,
        retrieval_method=retrieval_method,
    )

    # Gate 1 -- can we diagnose it at all? A complaint sharing no meaningful
    # word with the best section the search found is not in the manual.
    if diagnostic_overlap(complaint, heading, body) == 0:
        conv.escalation_detail = f"Closest section, \"{heading}\", shares no meaningful word with the complaint"
        conv.section_heading, conv.section_body, conv.available_steps = "", "", []
        conv.ticket = _escalate(conv, "unmatched", "Nothing in the product manual matches this complaint -- not guessing.")
        return conv

    # Gate 2 -- have we been here before? Same product, same manual section,
    # already handled recently: repeating the same step is not the answer.
    if source == "manual":
        prior = _find_recurrence(history, registration, heading)
        if prior:
            conv.escalation_detail = f"{heading} -- handled {prior.when:%d %b %Y} ({prior.outcome})"
            conv.ticket = _escalate(
                conv, "recurring",
                f"Recurring issue: '{heading}' was already handled on {prior.when:%d %b %Y} ({prior.outcome}).",
            )
            return conv

    if not available_steps:
        # Nothing in this section is a self-service step (e.g. it's a
        # pure "this needs a technician" section) -- escalate directly
        # rather than inventing a step that isn't there.
        conv.ticket = _escalate(conv, "no_steps", "No self-service step found in the relevant section.")
        return conv

    phrased = _tidy(str(agent(PHRASE_STEP_PROMPT.format(complaint=complaint, raw_step=available_steps[0]))))
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
        if current.attempt_number >= MAX_ATTEMPTS:
            code, reason = "attempts_exhausted", f"{MAX_ATTEMPTS} self-service attempts tried, issue persists."
        else:
            code, reason = "no_more_steps", "No further self-service step in the manual; needs a technician."
        conv.ticket = _escalate(conv, code, reason)
        return conv

    raw_step = conv.available_steps[next_index]
    phrased = _tidy(str(agent(PHRASE_STEP_PROMPT.format(complaint=conv.complaint, raw_step=raw_step))))
    conv.turns.append(Turn(attempt_number=current.attempt_number + 1, step=phrased))
    return conv


def _escalate(conv: Conversation, code: str, reason: str) -> Ticket:
    attempts = [t.step for t in conv.turns]
    ticket = Ticket(
        ticket_id=next_ticket_id(),
        customer_name=conv.registration.customer_name,
        customer_phone=conv.registration.customer_phone,
        product_name=conv.registration.product_name,
        serial_number=conv.registration.serial_number,
        product_id=conv.registration.product_id,
        issue_summary=f"{conv.complaint} -- {reason}",
        attempts_tried=attempts,
        safety_flag=conv.safety_flag,
        reason_code=code,
    )
    ticket.save()
    conv.escalation_code = code
    return ticket
