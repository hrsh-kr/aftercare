"""JSON files. Same layout the project always had: data/conversations/<id>.json,
data/tickets/<id>.json. Cases are not stored separately here -- they are derived from the
conversation files, so the file backend has no second copy to drift."""

import json
import os
import shutil
import uuid
from datetime import datetime
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

    # registry (a single json file)
    @property
    def _reg_file(self) -> Path:
        return self.conv_dir.parent / "registry.json"

    def _regs(self) -> dict:
        return json.loads(self._reg_file.read_text()) if self._reg_file.exists() else {}

    def put_registration(self, row: dict) -> None:
        regs = self._regs()
        regs[row["serial_number"]] = row
        self._reg_file.parent.mkdir(parents=True, exist_ok=True)
        self._reg_file.write_text(json.dumps(regs))

    def registrations_for_phone(self, phone: str) -> list[dict]:
        return sorted((r for r in self._regs().values() if r["customer_phone"] == phone), key=lambda r: r["serial_number"])

    def registrations(self, brand: str) -> list[dict]:
        return sorted((r for r in self._regs().values() if brand_for(r["product_id"]).lower() == brand), key=lambda r: r["serial_number"])

    def delete_registrations(self, source: str) -> int:
        regs = self._regs()
        keep = {k: v for k, v in regs.items() if v.get("source") != source}
        self._reg_file.write_text(json.dumps(keep))
        return len(regs) - len(keep)

    # chat channel
    def _chat_file(self, brand: str, phone: str) -> Path:
        return self.conv_dir.parent / "chats" / f"{brand}_{phone.lstrip('+')}.json"

    def _chat(self, brand: str, phone: str) -> dict:
        f = self._chat_file(brand, phone)
        return json.loads(f.read_text()) if f.exists() else {"messages": [], "state": {}}

    def _save_chat(self, brand: str, phone: str, chat: dict) -> None:
        f = self._chat_file(brand, phone)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(chat))

    def put_chat_message(self, brand: str, phone: str, msg: dict) -> str:
        chat = self._chat(brand, phone)
        sk = f"MSG#{datetime.now().isoformat()}#{uuid.uuid4().hex[:6]}"
        chat["messages"].append({**msg, "cursor": sk})
        self._save_chat(brand, phone, chat)
        return sk

    def chat_messages(self, brand: str, phone: str, after: str = "") -> list[dict]:
        return [m for m in self._chat(brand, phone)["messages"] if m["cursor"] > after]

    def get_chat_state(self, brand: str, phone: str) -> dict:
        return self._chat(brand, phone)["state"]

    def put_chat_state(self, brand: str, phone: str, state: dict) -> None:
        chat = self._chat(brand, phone)
        chat["state"] = state
        self._save_chat(brand, phone, chat)

    def put_chat_index(self, brand: str, phone: str, summary: dict) -> None:
        f = self.conv_dir.parent / "chat_index.json"
        idx = json.loads(f.read_text()) if f.exists() else {}
        idx[f"{brand}|{phone}"] = {**summary, "brand": brand}
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(idx))

    def chat_index(self, brand: str) -> list[dict]:
        f = self.conv_dir.parent / "chat_index.json"
        idx = json.loads(f.read_text()) if f.exists() else {}
        return sorted((v for v in idx.values() if v["brand"] == brand), key=lambda x: x.get("updated_at", ""), reverse=True)

    def clear(self) -> int:
        n = 0
        for extra in (self.conv_dir.parent / "chats", self.conv_dir.parent / "chat_index.json"):
            if extra.is_dir():
                shutil.rmtree(extra)
            elif extra.exists():
                extra.unlink()
        for d in (self.conv_dir, self.ticket_dir):
            if d.exists():
                n += len(list(d.glob("*.json")))
                shutil.rmtree(d)
        return n
