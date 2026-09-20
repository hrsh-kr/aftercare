"""JSON files. Same layout the project always had: data/conversations/<id>.json,
data/tickets/<id>.json. Cases are not stored separately here -- they are derived from the
conversation files, so the file backend has no second copy to drift."""

import json
import os
import shutil
from pathlib import Path

from src.layer1.catalog import brand_for

_ROOT = Path(os.environ.get("AFTERCARE_DATA_DIR", str(Path(__file__).resolve().parent.parent.parent / "data")))


class FileStore:
    name = "file"

    def __init__(self) -> None:
        self.conv_dir = _ROOT / "conversations"
        self.ticket_dir = _ROOT / "tickets"

    # conversations
    def put_conversation(self, conv_id: str, data: dict) -> None:
        self.conv_dir.mkdir(parents=True, exist_ok=True)
        (self.conv_dir / f"{conv_id}.json").write_text(json.dumps(data, indent=2))

    def get_conversation(self, conv_id: str) -> dict | None:
        path = self.conv_dir / f"{conv_id}.json"
        return json.loads(path.read_text()) if conv_id and path.exists() else None

    # tickets
    def put_ticket(self, brand: str, data: dict) -> None:
        self.ticket_dir.mkdir(parents=True, exist_ok=True)
        (self.ticket_dir / f"{data['ticket_id']}.json").write_text(json.dumps(data, indent=2))

    def tickets(self, brand: str | None = None) -> list[dict]:
        if not self.ticket_dir.exists():
            return []
        rows = [json.loads(p.read_text()) for p in self.ticket_dir.glob("*.json")]
        if brand:
            rows = [r for r in rows if r.get("product_id") and brand_for(r["product_id"]).lower() == brand]
        return sorted(rows, key=lambda r: r["ticket_id"])

    def get_ticket(self, ticket_id: str) -> dict | None:
        path = self.ticket_dir / f"{ticket_id}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def next_ticket_id(self) -> str:
        existing = list(self.ticket_dir.glob("*.json")) if self.ticket_dir.exists() else []
        return f"TBB-{len(existing) + 1:04d}"

    # cases (derived)
    def put_case(self, brand: str, case: dict) -> None:
        return None

    def _cases(self):
        for path in (self.conv_dir.glob("*.json") if self.conv_dir.exists() else []):
            try:
                c = json.loads(path.read_text())
            except ValueError:
                continue
            if not (c.get("resolved") or c.get("ticket") or c.get("answered")) or not c.get("created_at"):
                continue
            yield {
                "conversation_id": path.stem, "brand": brand_for(c["registration"]["product_id"]).lower(),
                "serial_number": c["registration"]["serial_number"], "section_heading": c.get("section_heading", ""),
                "source": "safety" if c.get("safety_flag") else c.get("source", ""),
                "outcome": "resolved" if c.get("resolved") else "answered" if c.get("answered") else "escalated",
                "reason_code": c.get("escalation_code", ""), "created_at": c["created_at"],
            }

    def cases_for_serial(self, serial: str, since_iso: str) -> list[dict]:
        return [c for c in self._cases() if c["serial_number"] == serial and c["created_at"] >= since_iso]

    def cases_for_brand(self, brand: str) -> list[dict]:
        return [c for c in self._cases() if c["brand"] == brand]

    def clear(self) -> int:
        n = 0
        for d in (self.conv_dir, self.ticket_dir):
            if d.exists():
                n += len(list(d.glob("*.json")))
                shutil.rmtree(d)
        return n
