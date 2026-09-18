"""6.3 -- the ranked view. The entry point of the company experience:
every candidate for one posting, sorted, no model call needed -- this
is a query and a sort over what Layer 1 already produced.

Ranked by evidence of genuine understanding (the bucket order below),
never by how impressive a repo looks -- DESIGN.md's fairness rule,
enforced structurally here rather than left to a scoring weight.
"""

from dataclasses import dataclass

from src.layer1.report import Report

BUCKET_ORDER = {"confirmed_good": 0, "not_enough_evidence": 1, "confirmed_bad": 2}


@dataclass
class RankedRow:
    candidate_id: str
    overall: str
    headline_evidence: str


def rank_candidates(reports: list[Report]) -> list[RankedRow]:
    rows = [
        RankedRow(
            candidate_id=r.candidate_id,
            overall=r.overall,
            headline_evidence=r.claims[0].reason if r.claims else "no claims checked",
        )
        for r in reports
    ]
    return sorted(rows, key=lambda row: BUCKET_ORDER.get(row.overall, 1))
