"""Escalated complaints -- created only when self-service didn't
resolve something, or on a safety flag. What each brand's own
dashboard (Cedar-authorized, src/webapp/api_core.py's dashboard_data())
reads from, filtered to that brand via product_id.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from src.domain.catalog import brand_for
from src.storage import get_store


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
        get_store().put_ticket(brand_for(self.product_id).lower() if self.product_id else "unknown", asdict(self))

    @staticmethod
    def load_all() -> list["Ticket"]:
        return [Ticket(**d) for d in get_store().tickets()]


def next_ticket_id() -> str:
    return get_store().next_ticket_id()
