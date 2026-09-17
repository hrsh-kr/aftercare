"""M.1 -- the flagship. TECHNICAL.md section 4, built for real:

1. Pick a starting point: the most substantial commit, or one already
   flagged 'plausible' rather than 'verified'.
2. Ask a broad question grounded in the real diff.
3. Score the answer 1-5 on specificity and reasoning, never shown to
   the candidate (DESIGN.md's rule against exposing thresholds).
4. Low score -> tighter follow-up on the same point. High score ->
   move to a different commit. Capped at MAX_TURNS.
5. Return the full transcript -- it joins the Layer 1 report, never a
   separate document.
"""

from dataclasses import dataclass, field
from typing import Callable

from strands import Agent
from strands.models.ollama import OllamaModel

MAX_TURNS = 6
DRILL_DOWN_THRESHOLD = 3  # score below this on a 1-5 scale triggers a tighter follow-up

FIRST_QUESTION_PROMPT = """You are interviewing a candidate about a specific \
commit in their own repository, to check they genuinely understand what they \
built -- not to catch them out, just to see clearly.

Commit diff:
{diff}

Ask one broad, open question about this specific change -- what it does and \
why they made this choice. Keep it to one or two sentences. Ask nothing else, \
just the question."""

FOLLOWUP_PROMPT = """The candidate was asked about this commit:
{diff}

They answered:
{answer}

Their answer scored {score}/5 for specificity and genuine understanding \
{low_or_high} the last question. {instruction}

Ask exactly one follow-up question, one or two sentences, nothing else."""

SCORE_PROMPT = """Score this candidate's answer from 1 to 5 for genuine, \
specific understanding of the actual code (not just plausible-sounding \
writing).

Score what they actually said, not whether they covered everything the \
diff contains -- a short answer that's specific and accurate about one \
part of the change is a 4 or 5, even if it doesn't mention every function \
in the diff. Only score low if what they said is generic, vague, wrong, or \
could apply to almost any code change.

A 5: references real specifics from the diff (an actual value, function \
name, or decision) and explains why, even briefly.
A 3: plausible but vague, or correct only at a surface level.
A 1: generic enough to describe almost any code change, or factually wrong.

Commit diff:
{diff}

Question asked: {question}

Candidate's answer: {answer}

Respond with only the number, nothing else."""


@dataclass
class Turn:
    question: str
    grounded_commit: str
    answer: str
    score: int
    next_action: str  # drill_deeper / move_on / end


@dataclass
class Conversation:
    turns: list[Turn] = field(default_factory=list)

    def transcript_text(self) -> str:
        lines = []
        for i, t in enumerate(self.turns, 1):
            lines.append(f"Q{i} (on {t.grounded_commit[:8]}): {t.question}")
            lines.append(f"A{i}: {t.answer}  [scored {t.score}/5]")
        return "\n".join(lines)

    def average_score(self) -> float:
        return sum(t.score for t in self.turns) / len(self.turns) if self.turns else 0.0


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    model = OllamaModel(host="http://localhost:11434", model_id=model_id)
    return Agent(model=model, callback_handler=None)


def _score(agent: Agent, diff: str, question: str, answer: str) -> int:
    raw = str(agent(SCORE_PROMPT.format(diff=diff, question=question, answer=answer))).strip()
    try:
        return max(1, min(5, int(raw.splitlines()[0].strip())))
    except (ValueError, IndexError):
        return 3  # ambiguous parse -- treat as "not enough evidence", not a failure


def run_m1_conversation(
    candidate_shas: list[str],
    get_diff: Callable[[str], str],
    get_answer: Callable[[str], str],
    agent: Agent | None = None,
    max_turns: int = MAX_TURNS,
) -> Conversation:
    """candidate_shas: commits to draw questions from, most substantial
    first. get_diff(sha) -> diff text. get_answer(question) -> the
    candidate's written answer -- a real prompt in the CLI, a canned
    string in tests."""
    agent = agent or _build_agent()
    conversation = Conversation()

    sha_queue = list(candidate_shas)
    current_sha = sha_queue.pop(0)
    diff = get_diff(current_sha)
    question = str(agent(FIRST_QUESTION_PROMPT.format(diff=diff))).strip()

    while len(conversation.turns) < max_turns:
        answer = get_answer(question)
        score = _score(agent, diff, question, answer)

        if score < DRILL_DOWN_THRESHOLD:
            next_action = "drill_deeper"
        elif sha_queue:
            next_action = "move_on"
        else:
            next_action = "end"

        conversation.turns.append(
            Turn(question=question, grounded_commit=current_sha, answer=answer, score=score, next_action=next_action)
        )

        if next_action == "end":
            break

        if next_action == "drill_deeper":
            instruction = "Ask a tighter, more specific follow-up on the exact same point -- give them a real chance to show they understand it."
            low_or_high = "below what a confident, specific answer would look like on"
        else:
            current_sha = sha_queue.pop(0)
            diff = get_diff(current_sha)
            instruction = "Move to this new commit -- ask a fresh broad question about it."
            low_or_high = "well on"

        question = str(
            agent(
                FOLLOWUP_PROMPT.format(
                    diff=diff, answer=answer, score=score, low_or_high=low_or_high, instruction=instruction
                )
            )
        ).strip()

    return conversation
