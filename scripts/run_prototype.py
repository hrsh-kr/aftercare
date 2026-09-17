"""The basic working prototype, end to end: Layer 1 -> Layer 2 ->
Layer 3a/3b, across more than one candidate so 6.3's ranking is real,
not a single row.

Run with GITHUB_TOKEN set: GITHUB_TOKEN=... python scripts/run_prototype.py
"""

import subprocess

from src.layer1.report import Report
from src.layer2.middleware import run_m1_conversation
from src.layer3a.feedback import generate_feedback
from src.layer3b.briefing import generate_briefing
from src.layer3b.decision import make_decision
from src.layer3b.ranking import rank_candidates
from src.pipeline import run_layer1

JOB_ID = "demo-job-1"


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    section("LAYER 1 -- candidate A (honest claim, our own real repo)")
    report_a = run_layer1(
        "candidate-a",
        "https://github.com/hrsh-kr/GroundTruth",
        ["I built a system that checks GitHub commit authorship and timeline "
         "patterns using Python, requests, and the Strands Agents SDK."],
        candidate_github_username="hrsh-kr",
    )
    for c in report_a.claims:
        print(f"{c.status}: {c.reason}")

    section("LAYER 1 -- candidate B (false claim, well-known public repo)")
    report_b = run_layer1(
        "candidate-b",
        "https://github.com/psf/requests",
        ["I built this as a JavaScript frontend framework for building UIs."],
        candidate_github_username="hrsh-kr",  # falsely claiming someone else's well-known repo
    )
    for c in report_b.claims:
        print(f"{c.status}: {c.reason}")

    section("LAYER 2 -- M.1 conversation with candidate A")

    def get_diff(sha: str) -> str:
        return subprocess.run(["git", "show", sha], capture_output=True, text=True, check=True).stdout

    canned_answers = iter([
        "authorship_share divides the claimed author's changed lines by the "
        "total across all commits -- I made it return 0.0 for an empty commit "
        "list instead of raising, so a candidate with no history reads as "
        "'not enough evidence' rather than crashing the whole pipeline.",
        "timeline_shape classifies the pattern as bulk if one commit accounts "
        "for over 80% of all changed lines, regardless of spacing, since a "
        "single dominant commit is the stronger signal either way.",
    ])

    def get_answer(question: str) -> str:
        print(f"Q: {question}")
        answer = next(canned_answers, "I'm not sure, I'd need to look at it again.")
        print(f"A: {answer}")
        return answer

    conversation = run_m1_conversation(
        ["f139654c277e4ec5df9c79ae36c130a50a10a7d5"],
        get_diff,
        get_answer,
        max_turns=2,
    )
    print(f"\naverage score: {conversation.average_score():.1f}/5")

    section("LAYER 3A -- candidate feedback (5.1) for candidate A")
    print(generate_feedback(report_a, conversation))

    section("LAYER 3B -- interviewer briefing (6.1) for candidate A")
    print(generate_briefing(report_a, conversation))

    section("LAYER 3B -- decision record (6.2) for candidate A")
    decision = make_decision(
        JOB_ID,
        report_a,
        interviewer_notes="Candidate was specific and confident about the edge-case "
        "handling, referenced exact thresholds unprompted.",
        interview_transcript="Interviewer: Walk me through the zero-commit case. "
        "Candidate: [as above, matches M.1 transcript closely].",
    )
    print(decision.final_reasoning)

    section("LAYER 3B -- ranked view (6.3) across both candidates")
    for row in rank_candidates([report_a, report_b]):
        print(f"{row.overall:<22} {row.candidate_id:<15} {row.headline_evidence}")


if __name__ == "__main__":
    main()
