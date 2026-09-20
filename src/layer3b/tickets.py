"""Escalated complaints -- created only when self-service didn't
resolve something, or on a safety flag. What each brand's own
dashboard (Cedar-authorized, src/webapp/api_core.py's dashboard_data())
reads from, filtered to that brand via product_id.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# Overridable: real Lambda's code mount (/var/task) is read-only, only
# /tmp is writable -- SAM Local enforces this too, caught it by actually
# running against it (see IMPLEMENTATION.md Phase 7.5). The SAM template
# sets AFTERCARE_DATA_DIR=/tmp/aftercare-data for the Lambda functions;
# Flask keeps writing into the repo's data/ so it's easy to inspect.
_DATA_ROOT = Path(os.environ.get("AFTERCARE_DATA_DIR", str(Path(__file__).resolve().parent.parent.parent / "data")))
DATA_DIR = _DATA_ROOT / "tickets"


@dataclass
class Ticket:
    ticket_id: str
    customer_name: str
    customer_phone: str
    product_name: str
    serial_number: str
    issue_summary: str
    product_id: str = ""  # e.g. "AC-CB-15T" -- which brand this ticket belongs to, by prefix
    reason_code: str = ""  # why a person was needed -- see agent.ESCALATION_LABELS
    attempts_tried: list[str] = field(default_factory=list)
    safety_flag: bool = False
    status: str = "new"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / f"{self.ticket_id}.json").write_text(json.dumps(asdict(self), indent=2))

    @staticmethod
    def load_all() -> list["Ticket"]:
        if not DATA_DIR.exists():
            return []
        tickets = []
        for path in DATA_DIR.glob("*.json"):
            data = json.loads(path.read_text())
            tickets.append(Ticket(**data))
        return tickets


def next_ticket_id() -> str:
    existing = list(DATA_DIR.glob("*.json")) if DATA_DIR.exists() else []
    return f"TBB-{len(existing) + 1:04d}"
