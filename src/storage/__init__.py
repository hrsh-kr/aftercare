"""Storage behind one interface, two implementations.

  file      JSON files under data/ -- zero setup, what the Flask dev server uses.
  dynamodb  one DynamoDB table (DynamoDB Local via DYNAMODB_ENDPOINT, real DynamoDB
            when it's unset) -- what the Lambdas use, because a Lambda has no disk to keep.

Chosen by AFTERCARE_STORE (default "file"). The rest of the code never knows which.
`Store` documents the access patterns the application actually needs; the DynamoDB
key design that serves them is in docs/DYNAMODB_DESIGN.md.
"""

import os
from typing import Protocol


class Store(Protocol):
    name: str

    def put_conversation(self, conv_id: str, data: dict) -> None: ...
    def get_conversation(self, conv_id: str) -> dict | None: ...

    def put_ticket(self, brand: str, data: dict) -> None: ...
    def tickets(self, brand: str | None = None) -> list[dict]: ...
    def get_ticket(self, ticket_id: str) -> dict | None: ...
    def next_ticket_id(self) -> str: ...

    def put_case(self, brand: str, case: dict) -> None: ...
    def cases_for_serial(self, serial: str, since_iso: str) -> list[dict]: ...
    def cases_for_brand(self, brand: str) -> list[dict]: ...

    def clear(self) -> int: ...


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        kind = os.environ.get("AFTERCARE_STORE", "file").lower()
        if kind == "dynamodb":
            from src.storage.dynamodb_store import DynamoStore
            _store = DynamoStore()
        elif kind == "file":
            from src.storage.file_store import FileStore
            _store = FileStore()
        else:
            raise RuntimeError(f"AFTERCARE_STORE must be 'file' or 'dynamodb', not {kind!r}")
    return _store


def reset_store_for_tests() -> None:
    global _store
    _store = None
