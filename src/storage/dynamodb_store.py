"""One DynamoDB table, single-table design. Full reasoning: docs/DYNAMODB_DESIGN.md.

  item              PK               SK                     GSI1PK           GSI1SK
  conversation      CONV#<id>        STATE                  -                -
  ticket            BRAND#<brand>    TICKET#<id>            TICKET#<id>      BRAND#<brand>
  case              BRAND#<brand>    CASE#<iso>#<conv id>   SERIAL#<serial>  CASE#<iso>
  ticket counter    CTR              TICKET                 -                -

Endpoint: DYNAMODB_ENDPOINT points at DynamoDB Local (the AWS-provided emulator, no account).
Unset it and boto3 talks to real DynamoDB with normal credentials -- nothing else changes.
"""

import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

TABLE = os.environ.get("AFTERCARE_TABLE", "aftercare")
ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")
CONV_TTL_SECONDS = 7 * 24 * 3600


class DynamoStore:
    name = "dynamodb"

    def __init__(self) -> None:
        kwargs = {"region_name": os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))}
        if ENDPOINT:  # DynamoDB Local accepts any credentials, but boto3 insists on having some
            kwargs.update(endpoint_url=ENDPOINT, aws_access_key_id="local", aws_secret_access_key="local")
        self._ddb = boto3.resource("dynamodb", **kwargs)
        self._table = self._ddb.Table(TABLE)
        if ENDPOINT:
            self._ensure_table()

    def _ensure_table(self) -> None:
        """Local convenience only. In a real account the table comes from template.yaml."""
        try:
            self._table.load()
            return
        except self._ddb.meta.client.exceptions.ResourceNotFoundException:
            pass
        self._ddb.create_table(
            TableName=TABLE, BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": n, "AttributeType": "S"} for n in ("PK", "SK", "GSI1PK", "GSI1SK")],
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            GlobalSecondaryIndexes=[{
                "IndexName": "GSI1", "Projection": {"ProjectionType": "ALL"},
                "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"}, {"AttributeName": "GSI1SK", "KeyType": "RANGE"}],
            }],
        )
        self._table.wait_until_exists()
        try:
            self._ddb.meta.client.update_time_to_live(TableName=TABLE, TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"})
        except Exception:
            pass

    # conversations: one item, the whole state as JSON (it is only ever read back whole)
    def put_conversation(self, conv_id: str, data: dict) -> None:
        self._table.put_item(Item={"PK": f"CONV#{conv_id}", "SK": "STATE", "data": json.dumps(data),
                                   "ttl": int(time.time()) + CONV_TTL_SECONDS})

    def get_conversation(self, conv_id: str) -> dict | None:
        if not conv_id:
            return None
        item = self._table.get_item(Key={"PK": f"CONV#{conv_id}", "SK": "STATE"}, ConsistentRead=True).get("Item")
        return json.loads(item["data"]) if item else None

    # tickets
    def put_ticket(self, brand: str, data: dict) -> None:
        self._table.put_item(Item={**data, "PK": f"BRAND#{brand}", "SK": f"TICKET#{data['ticket_id']}",
                                   "GSI1PK": f"TICKET#{data['ticket_id']}", "GSI1SK": f"BRAND#{brand}"})

    @staticmethod
    def _strip(item: dict) -> dict:
        return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "ttl")}

    def tickets(self, brand: str | None = None) -> list[dict]:
        if brand:
            r = self._table.query(KeyConditionExpression=Key("PK").eq(f"BRAND#{brand}") & Key("SK").begins_with("TICKET#"))
            return sorted((self._strip(i) for i in r["Items"]), key=lambda t: t["ticket_id"])
        rows = []  # only the demo's "show me everything" path; never on a request hot path
        for b in ("aquaspin", "arcticair"):
            rows += self.tickets(b)
        return sorted(rows, key=lambda t: t["ticket_id"])

    def get_ticket(self, ticket_id: str) -> dict | None:
        r = self._table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"TICKET#{ticket_id}"), Limit=1)
        return self._strip(r["Items"][0]) if r["Items"] else None

    def next_ticket_id(self) -> str:
        """Atomic counter: ADD returns the new value, so two concurrent escalations can never share an id."""
        r = self._table.update_item(Key={"PK": "CTR", "SK": "TICKET"}, UpdateExpression="ADD n :one",
                                    ExpressionAttributeValues={":one": 1}, ReturnValues="UPDATED_NEW")
        return f"TBB-{int(r['Attributes']['n']):04d}"

    # cases
    def put_case(self, brand: str, case: dict) -> None:
        iso = case["created_at"]
        self._table.put_item(Item={**case, "PK": f"BRAND#{brand}", "SK": f"CASE#{iso}#{case['conversation_id']}",
                                   "GSI1PK": f"SERIAL#{case['serial_number']}", "GSI1SK": f"CASE#{iso}"})

    def cases_for_serial(self, serial: str, since_iso: str) -> list[dict]:
        r = self._table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"SERIAL#{serial}") & Key("GSI1SK").gte(f"CASE#{since_iso}"))
        return [self._strip(i) for i in r["Items"]]

    def cases_for_brand(self, brand: str) -> list[dict]:
        r = self._table.query(KeyConditionExpression=Key("PK").eq(f"BRAND#{brand}") & Key("SK").begins_with("CASE#"))
        return [self._strip(i) for i in r["Items"]]

    def clear(self) -> int:
        n = 0
        for item in self._table.scan(ProjectionExpression="PK, SK")["Items"]:
            self._table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            n += 1
        return n
