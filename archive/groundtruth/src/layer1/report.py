"""The Layer 1 report, and where it lives.

DESIGN.md's data model (TECHNICAL.md section 3) calls this a DynamoDB
table. For this prototype it's a JSON file per candidate under
data/reports/ -- same shape, same keys, swappable for a real or
LocalStack-emulated table later without changing anything upstream.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.layer1.claim_match import ClaimResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "reports"


@dataclass
class Report:
    candidate_id: str
    repo_url: str
    claims: list[ClaimResult] = field(default_factory=list)

    @property
    def overall(self) -> str:
        """Roll many per-claim statuses up into the three-bucket read
        DESIGN.md's ranked view (6.3) actually shows: confirmed_good,
        not_enough_evidence, confirmed_bad. Detail stays available per
        claim for 6.1's briefing -- this is only the summary."""
        statuses = [c.status for c in self.claims]
        if not statuses:
            return "not_enough_evidence"
        if "inconsistent" in statuses:
            return "confirmed_bad"
        if all(s in ("verified", "plausible") for s in statuses):
            return "confirmed_good"
        return "not_enough_evidence"

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / f"{self.candidate_id}.json"
        path.write_text(json.dumps(asdict(self), indent=2))

    @staticmethod
    def load(candidate_id: str) -> "Report":
        path = DATA_DIR / f"{candidate_id}.json"
        data = json.loads(path.read_text())
        return Report(
            candidate_id=data["candidate_id"],
            repo_url=data["repo_url"],
            claims=[ClaimResult(**c) for c in data["claims"]],
        )

    @staticmethod
    def load_all() -> list["Report"]:
        if not DATA_DIR.exists():
            return []
        return [Report.load(p.stem) for p in DATA_DIR.glob("*.json")]
