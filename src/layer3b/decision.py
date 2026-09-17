"""6.2 -- the decision record. Combines our evidence with what
actually happened in the human interview, so the final record
reflects both, not just our half.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from strands import Agent
from strands.models.ollama import OllamaModel

from src.layer1.report import Report

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "decisions"

DECISION_PROMPT = """Write a short, defensible hiring decision record combining \
two sources of evidence: our automated report, and the human interviewer's own \
notes and transcript from the live round. Two to four sentences. State the \
outcome and the specific reasons from both sources -- this has to hold up if \
someone asks "why" months later.

Automated evidence:
{claims_summary}

Human interviewer's notes:
{interviewer_notes}

Human interview transcript:
{interview_transcript}"""


@dataclass
class Decision:
    job_id: str
    candidate_id: str
    rank_bucket: str
    interviewer_notes: str
    interview_transcript: str
    final_reasoning: str

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / f"{self.job_id}__{self.candidate_id}.json").write_text(json.dumps(asdict(self), indent=2))


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    return Agent(model=OllamaModel(host="http://localhost:11434", model_id=model_id), callback_handler=None)


def make_decision(
    job_id: str,
    report: Report,
    interviewer_notes: str,
    interview_transcript: str,
    agent: Agent | None = None,
) -> Decision:
    agent = agent or _build_agent()
    claims_summary = "\n".join(f"- \"{c.claim}\": {c.status} -- {c.reason}" for c in report.claims)

    reasoning = str(
        agent(
            DECISION_PROMPT.format(
                claims_summary=claims_summary,
                interviewer_notes=interviewer_notes,
                interview_transcript=interview_transcript,
            )
        )
    ).strip()

    decision = Decision(
        job_id=job_id,
        candidate_id=report.candidate_id,
        rank_bucket=report.overall,
        interviewer_notes=interviewer_notes,
        interview_transcript=interview_transcript,
        final_reasoning=reasoning,
    )
    decision.save()
    return decision
