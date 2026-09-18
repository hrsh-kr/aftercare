"""5.1 -- feedback that can't become a patch list.

DESIGN.md's two rules, enforced by what we hand the model, not just
asked of it: tell the candidate what could/couldn't be verified (the
per-claim status and reason already have that); never expose exact
thresholds or weights (so those numbers never enter this prompt at
all -- only the status and reason strings do).
"""

from strands import Agent
from strands.models.ollama import OllamaModel

from src.layer1.report import Report
from src.layer2.middleware import Conversation

FEEDBACK_PROMPT = """Write brief, honest feedback for a candidate based on \
what was checked about their project claims. Rules:
- State what was verified, what was inconsistent, and what there wasn't \
enough evidence for -- in plain language, one line per claim.
- Never mention specific numbers, percentages, thresholds, or how anything \
was weighed or scored.
- If anything was inconsistent or lacked evidence, end by pointing them to \
the conversation about their own repo as the real way to demonstrate \
understanding -- not a list of things to go edit.
- Two to four sentences total. Direct, not harsh.

Claims checked:
{claims_summary}

{conversation_note}"""


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    return Agent(model=OllamaModel(host="http://localhost:11434", model_id=model_id), callback_handler=None)


def generate_feedback(report: Report, conversation: Conversation | None = None, agent: Agent | None = None) -> str:
    agent = agent or _build_agent()

    claims_summary = "\n".join(f"- \"{c.claim}\": {c.status} -- {c.reason}" for c in report.claims)

    if conversation and conversation.turns:
        conversation_note = (
            f"They also had a {len(conversation.turns)}-question conversation about their own repo, "
            f"which the feedback can reference as already having happened."
        )
    else:
        conversation_note = "They have not yet had the follow-up conversation about their own repo."

    return str(agent(FEEDBACK_PROMPT.format(claims_summary=claims_summary, conversation_note=conversation_note))).strip()
