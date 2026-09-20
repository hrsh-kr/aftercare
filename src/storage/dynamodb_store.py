"""One DynamoDB table, single-table design. The tables come from template.yaml (in an account) or
scripts/bootstrap_local.py (DynamoDB Local); this class never creates them, and a missing table or
unreachable endpoint is a DependencyUnavailable, not a silent alternative. Full reasoning: docs/DYNAMODB_DESIGN.md.

  item              PK               SK                     GSI1PK           GSI1SK
  conversation      CONV#<id>        STATE                  -                -
  ticket            BRAND#<brand>    TICKET#<id>            TICKET#<id>      BRAND#<brand>
  case              BRAND#<brand>    CASE#<iso>#<conv id>   SERIAL#<serial>  CASE#<iso>
  ticket counter    CTR              TICKET                 -                -

Endpoint: DYNAMODB_ENDPOINT points at DynamoDB Local (the AWS-provided emulator, no account).
Unset it and boto3 talks to real DynamoDB with normal credentials -- nothing else changes.
"""

import functools
import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import BotoCoreError, ClientError

from src.errors import DependencyUnavailable

TABLE = os.environ.get("AFTERCARE_TABLE", "AftercareTable")
ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")
CONV_TTL_SECONDS = 7 * 24 * 3600


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except (BotoCoreError, ClientError) as exc:
            raise DependencyUnavailable("DynamoDB", str(exc)[:160]) from exc
    return wrapper


class DynamoStore:
    name = "dynamodb"

    def __init__(self) -> None:
        kwargs = {"region_name": os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))}
        if ENDPOINT:  # DynamoDB Local accepts any credentials, but boto3 insists on having some
            kwargs.update(endpoint_url=ENDPOINT, aws_access_key_id="local", aws_secret_access_key="local")
        self._ddb = boto3.resource("dynamodb", **kwargs)
        self._table = self._ddb.Table(TABLE)

    # conversations: one item, the whole state as JSON (it is only ever read back whole)
    @_guard
    def put_conversation(self, conv_id: str, data: dict) -> None:
        self._table.put_item(Item={"PK": f"CONV#{conv_id}", "SK": "STATE", "data": json.dumps(data),
                                   "ttl": int(time.time()) + CONV_TTL_SECONDS})

    @_guard
    def get_conversation(self, conv_id: str) -> dict | None:
        if not conv_id:
            return None
        item = self._table.get_item(Key={"PK": f"CONV#{conv_id}", "SK": "STATE"}, ConsistentRead=True).get("Item")
        return json.loads(item["data"]) if item else None

    # tickets
    @_guard
    def put_ticket(self, brand: str, data: dict) -> None:
        self._table.put_item(Item={**data, "PK": f"BRAND#{brand}", "SK": f"TICKET#{data['ticket_id']}",
                                   "GSI1PK": f"TICKET#{data['ticket_id']}", "GSI1SK": f"BRAND#{brand}"})

    @staticmethod
    def _strip(item: dict) -> dict:
        return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "ttl")}

    @_guard
    def tickets(self, brand: str | None = None) -> list[dict]:
        if brand:
            r = self._table.query(KeyConditionExpression=Key("PK").eq(f"BRAND#{brand}") & Key("SK").begins_with("TICKET#"))
            return sorted((self._strip(i) for i in r["Items"]), key=lambda t: t["ticket_id"])
        rows = []  # only the demo's "show me everything" path; never on a request hot path
        for b in ("aquaspin", "arcticair"):
            rows += self.tickets(b)
        return sorted(rows, key=lambda t: t["ticket_id"])

    @_guard
    def get_ticket(self, ticket_id: str) -> dict | None:
        r = self._table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"TICKET#{ticket_id}"), Limit=1)
        return self._strip(r["Items"][0]) if r["Items"] else None

    @_guard
    def next_ticket_id(self) -> str:
        """Atomic counter: ADD returns the new value, so two concurrent escalations can never share an id."""
        r = self._table.update_item(Key={"PK": "CTR", "SK": "TICKET"}, UpdateExpression="ADD n :one",
                                    ExpressionAttributeValues={":one": 1}, ReturnValues="UPDATED_NEW")
        return f"TBB-{int(r['Attributes']['n']):04d}"

    # cases
    @_guard
    def put_case(self, brand: str, case: dict) -> None:
        iso = case["created_at"]
        self._table.put_item(Item={**case, "PK": f"BRAND#{brand}", "SK": f"CASE#{iso}#{case['conversation_id']}",
                                   "GSI1PK": f"SERIAL#{case['serial_number']}", "GSI1SK": f"CASE#{iso}"})

    @_guard
    def cases_for_serial(self, serial: str, since_iso: str) -> list[dict]:
        r = self._table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"SERIAL#{serial}") & Key("GSI1SK").gte(f"CASE#{since_iso}"))
        return [self._strip(i) for i in r["Items"]]

    @_guard
    def cases_for_brand(self, brand: str) -> list[dict]:
        r = self._table.query(KeyConditionExpression=Key("PK").eq(f"BRAND#{brand}") & Key("SK").begins_with("CASE#"))
        return [self._strip(i) for i in r["Items"]]

    # registry: PK BRAND#<brand>, SK REG#<serial>; GSI1 PHONE#<phone> finds a customer's products
    @staticmethod
    def _plain(item: dict) -> dict:
        out = {}
        for k, v in DynamoStore._strip(item).items():
            out[k] = int(v) if isinstance(v, Decimal) else v
        return out

    @_guard
    def put_registration(self, row: dict) -> None:
        from src.domain.catalog import brand_for
        brand = brand_for(row["product_id"]).lower()
        self._table.put_item(Item={**row, "PK": f"BRAND#{brand}", "SK": f"REG#{row['serial_number']}",
                                   "GSI1PK": f"PHONE#{row['customer_phone']}", "GSI1SK": f"REG#{row['serial_number']}"})

    @_guard
    def registrations_for_phone(self, phone: str) -> list[dict]:
        r = self._table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"PHONE#{phone}") & Key("GSI1SK").begins_with("REG#"))
        return sorted((self._plain(i) for i in r["Items"]), key=lambda x: x["serial_number"])

    @_guard
    def registrations(self, brand: str) -> list[dict]:
        r = self._table.query(KeyConditionExpression=Key("PK").eq(f"BRAND#{brand}") & Key("SK").begins_with("REG#"))
        return sorted((self._plain(i) for i in r["Items"]), key=lambda x: x["serial_number"])

    @_guard
    def delete_registrations(self, source: str) -> int:
        n = 0
        for b in ("aquaspin", "arcticair"):
            for item in self.registrations(b):
                if item.get("source") == source:
                    self._table.delete_item(Key={"PK": f"BRAND#{b}", "SK": f"REG#{item['serial_number']}"})
                    n += 1
        return n

    # WhatsApp channel. Messages: PK CHAT#<brand>#<phone>, SK MSG#<iso>#<id> (time-ordered, so "after"
    # is a plain range condition). State: same PK, SK STATE. Inbox: PK BRAND#<brand>, SK CHATIDX#<phone>.
    @_guard
    def put_chat_message(self, brand: str, phone: str, msg: dict) -> str:
        from datetime import datetime
        sk = f"MSG#{datetime.now().isoformat()}#{uuid.uuid4().hex[:6]}"
        self._table.put_item(Item={**msg, "PK": f"CHAT#{brand}#{phone}", "SK": sk, "ttl": int(time.time()) + CONV_TTL_SECONDS})
        return sk

    @_guard
    def chat_messages(self, brand: str, phone: str, after: str = "") -> list[dict]:
        cond = Key("PK").eq(f"CHAT#{brand}#{phone}")
        cond = cond & (Key("SK").gt(after) if after else Key("SK").begins_with("MSG#"))
        items = self._table.query(KeyConditionExpression=cond)["Items"]
        return [{**self._strip_msg(i), "cursor": i["SK"]} for i in items if i["SK"].startswith("MSG#")]

    @staticmethod
    def _native(v):
        """boto3 returns numbers as Decimal; the API speaks JSON."""
        if isinstance(v, Decimal):
            return int(v) if v == v.to_integral_value() else float(v)
        if isinstance(v, dict):
            return {k: DynamoStore._native(x) for k, x in v.items()}
        if isinstance(v, list):
            return [DynamoStore._native(x) for x in v]
        return v

    @staticmethod
    def _strip_msg(item: dict) -> dict:
        return DynamoStore._native({k: v for k, v in item.items() if k not in ("PK", "SK", "ttl")})

    @_guard
    def get_chat_state(self, brand: str, phone: str) -> dict:
        item = self._table.get_item(Key={"PK": f"CHAT#{brand}#{phone}", "SK": "STATE"}, ConsistentRead=True).get("Item")
        return json.loads(item["data"]) if item else {}

    @_guard
    def put_chat_state(self, brand: str, phone: str, state: dict) -> None:
        self._table.put_item(Item={"PK": f"CHAT#{brand}#{phone}", "SK": "STATE", "data": json.dumps(state), "ttl": int(time.time()) + CONV_TTL_SECONDS})

    @_guard
    def put_chat_index(self, brand: str, phone: str, summary: dict) -> None:
        self._table.put_item(Item={**summary, "PK": f"BRAND#{brand}", "SK": f"CHATIDX#{phone}"})

    @_guard
    def chat_index(self, brand: str) -> list[dict]:
        r = self._table.query(KeyConditionExpression=Key("PK").eq(f"BRAND#{brand}") & Key("SK").begins_with("CHATIDX#"))
        return sorted((self._plain(i) for i in r["Items"]), key=lambda x: x.get("updated_at", ""), reverse=True)

    @_guard
    def clear(self) -> int:
        """Runtime data (conversations, tickets, cases, chats, counters). The registry is kept: it is
        loaded data, not something a demo run produced. delete_registrations() clears sandbox uploads."""
        n = 0
        scan = self._table.scan(ProjectionExpression="PK, SK")
        for item in scan["Items"]:
            if item["SK"].startswith("REG#"):
                continue
            self._table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            n += 1
        return n
