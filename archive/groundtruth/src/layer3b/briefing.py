"""6.1 -- the interviewer briefing. The evidence-backed report plus
the full M.1 transcript (not just a score) plus specific next
questions, grounded in this candidate's actual commits.
"""

from strands import Agent
from strands.models.ollama import OllamaModel

from src.layer1.report import Report
from src.layer2.middleware import Conversation

BRIEFING_PROMPT = """Write a short interview briefing for whoever runs the \
next round with this candidate. Include:
1. A one-line summary of what checked out and what didn't, from the claims below.
2. Two specific questions to ask next, grounded in the actual evidence or \
conversation below -- not generic questions.

Claims checked:
{claims_summary}

{conversation_summary}

Keep it under 120 words, direct, written for a busy interviewer."""


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    return Agent(model=OllamaModel(host="http://localhost:11434", model_id=model_id), callback_handler=None)


def generate_briefing(report: Report, conversation: Conversation | None = None, agent: Agent | None = None) -> str:
    agent = agent or _build_agent()

    claims_summary = "\n".join(f"- \"{c.claim}\": {c.status} -- {c.reason}" for c in report.claims)
    conversation_summary = (
        f"M.1 conversation transcript:\n{conversation.transcript_text()}"
        if conversation and conversation.turns
        else "No M.1 conversation has run yet for this candidate."
    )

    briefing_text = str(
        agent(BRIEFING_PROMPT.format(claims_summary=claims_summary, conversation_summary=conversation_summary))
    ).strip()

    # The full transcript is included verbatim, not just summarized --
    # DESIGN.md is explicit that 6.1 carries the transcript itself.
    if conversation and conversation.turns:
        briefing_text += f"\n\n--- Full M.1 transcript ---\n{conversation.transcript_text()}"

    return briefing_text
