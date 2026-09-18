"""Deterministic checks on a commit history — no model involved.

These run before Bedrock/the local model sees anything, per DESIGN.md
Layer 1, step 3: read the pattern of commits, not just their content.
"""

from dataclasses import dataclass
from statistics import mean, pstdev


@dataclass
class Commit:
    author: str
    timestamp: float  # unix seconds
    lines_changed: int


def authorship_share(commits: list[Commit], claimed_author: str) -> float:
    """Fraction of total changed lines attributed to the claimed author.

    Zero commits returns 0.0 rather than raising — an empty repo is
    "not enough evidence", not a division error.
    """
    total = sum(c.lines_changed for c in commits)
    if total == 0:
        return 0.0
    theirs = sum(c.lines_changed for c in commits if c.author == claimed_author)
    return theirs / total


def timeline_shape(commits: list[Commit]) -> str:
    """Classify the commit pattern as "iterative", "bulk", or "insufficient".

    Iterative: several commits, spread out — the pattern a real,
    hands-on debugging process leaves behind.
    Bulk: one or two commits carrying almost all the change — could be
    an honest one-time upload, could be a dump. Not a verdict on its
    own; see DESIGN.md's fairness rules.
    """
    if len(commits) < 2:
        return "insufficient"

    ordered = sorted(commits, key=lambda c: c.timestamp)
    gaps = [b.timestamp - a.timestamp for a, b in zip(ordered, ordered[1:])]
    total_lines = sum(c.lines_changed for c in commits)
    largest_commit_share = max(c.lines_changed for c in commits) / total_lines if total_lines else 0

    spread_out = mean(gaps) > 0 and pstdev(gaps) < mean(gaps) * 2
    if largest_commit_share > 0.8:
        return "bulk"
    if spread_out and len(commits) >= 4:
        return "iterative"
    return "insufficient"
