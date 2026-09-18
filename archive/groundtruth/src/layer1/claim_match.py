"""The one step in Layer 1 that needs actual judgment, not just
counting: does a candidate's claim plausibly match the real evidence.

DESIGN.md, Layer 1, step 4-5: per-claim status is verified / plausible
/ inconsistent / not enough evidence, always with the evidence shown.
"""

import json
from dataclasses import dataclass, field

from strands import Agent
from strands.models.ollama import OllamaModel

STATUSES = ("verified", "plausible", "inconsistent", "insufficient")

CLAIM_MATCH_PROMPT = """You are checking whether a candidate's claim about a \
project is backed up by real evidence from their repository. Be skeptical but \
fair -- the goal is accuracy, not suspicion.

Claim: {claim}

Evidence:
- Repository dependency files found: {dep_files}
- Dependency file contents (truncated): {dep_contents}
- Commit authorship: {author_share:.0%} of changed lines are from the \
claimed author, across {commit_count} recent commits
- Commit pattern: {timeline_shape}
- Fork status: {fork_status}

Decide one status for this claim:
- "verified": the dependency evidence and commit pattern directly support \
the claim
- "plausible": some evidence supports it, but not conclusively
- "inconsistent": the evidence contradicts the claim (e.g. claimed \
technology isn't actually used, or authorship is mostly someone else's)
- "insufficient": not enough evidence either way (e.g. very few commits, \
or the claim doesn't reference anything checkable)

Respond with exactly this format, nothing else:
STATUS: <one of the four above>
REASON: <one sentence, citing the specific evidence above>"""


@dataclass
class ClaimResult:
    claim: str
    status: str
    reason: str
    evidence: dict = field(default_factory=dict)


def _build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    model = OllamaModel(host="http://localhost:11434", model_id=model_id)
    return Agent(model=model, callback_handler=None)  # no live token streaming to stdout


def check_claim(
    claim: str,
    author_share: float,
    commit_count: int,
    timeline_shape: str,
    is_fork: bool,
    parent_full_name: str | None,
    dependency_files: dict[str, str],
    agent: Agent | None = None,
) -> ClaimResult:
    agent = agent or _build_agent()

    dep_contents = "\n".join(f"{name}: {content[:300]}" for name, content in dependency_files.items())
    if is_fork:
        fork_status = f"this IS a fork, of {parent_full_name}" if parent_full_name else "this IS a fork"
    else:
        fork_status = "this is NOT a fork -- it's an original repository"

    prompt = CLAIM_MATCH_PROMPT.format(
        claim=claim,
        dep_files=list(dependency_files.keys()) or "none found",
        dep_contents=dep_contents or "none",
        author_share=author_share,
        commit_count=commit_count,
        timeline_shape=timeline_shape,
        fork_status=fork_status,
    )

    raw = str(agent(prompt)).strip()

    status, reason = "insufficient", raw
    for line in raw.splitlines():
        if line.upper().startswith("STATUS:"):
            candidate_status = line.split(":", 1)[1].strip().lower()
            if candidate_status in STATUSES:
                status = candidate_status
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()

    return ClaimResult(
        claim=claim,
        status=status,
        reason=reason,
        evidence={
            "author_share": author_share,
            "commit_count": commit_count,
            "timeline_shape": timeline_shape,
            "is_fork": is_fork,
            "dependency_files": list(dependency_files.keys()),
        },
    )
