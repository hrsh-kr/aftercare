"""Escalated complaints -- created only when self-service didn't
resolve something, or on a safety flag. What the brand dashboard
(Phase 6) reads from.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tickets"


@dataclass
class Ticket:
    ticket_id: str
    customer_name: str
    customer_phone: str
    product_name: str
    serial_number: str
    issue_summary: str
    product_id: str = ""  # e.g. "AC-CB-15T" -- which brand this ticket belongs to, by prefix
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
