"""Idempotent conversation start, using Lambda Powertools' idempotency utility.

Why: an API Gateway client (or a flaky mobile network) retries. Without this, one customer
message can open two conversations and escalate to two tickets. With it, the first call does
the work and stores its result in a DynamoDB table (with a TTL); a retry carrying the same
Idempotency-Key within the window gets the stored result back, byte for byte. Same key with
different content is rejected, not silently answered.
"""

import os

import boto3
from aws_lambda_powertools.utilities.idempotency import DynamoDBPersistenceLayer, IdempotencyConfig, idempotent_function

from src.storage import dynamodb_store

TABLE = os.environ.get("AFTERCARE_IDEMPOTENCY_TABLE", "aftercare-idempotency")


def _client():
    kwargs = {"region_name": os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))}
    if dynamodb_store.ENDPOINT:
        kwargs.update(endpoint_url=dynamodb_store.ENDPOINT, aws_access_key_id="local", aws_secret_access_key="local")
    return boto3.client("dynamodb", **kwargs)


_client_ = _client()
if dynamodb_store.ENDPOINT:  # local convenience; in an account template.yaml owns the table
    try:
        _client_.describe_table(TableName=TABLE)
    except _client_.exceptions.ResourceNotFoundException:
        _client_.create_table(TableName=TABLE, BillingMode="PAY_PER_REQUEST",
                              AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                              KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}])
        _client_.get_waiter("table_exists").wait(TableName=TABLE)

_persistence = DynamoDBPersistenceLayer(table_name=TABLE, boto3_client=_client_)
_config = IdempotencyConfig(event_key_jmespath="key", payload_validation_jmespath="[phone, complaint, product_id]", expires_after_seconds=60)


@idempotent_function(data_keyword_argument="payload", persistence_store=_persistence, config=_config)
def once(payload: dict) -> dict:
    from src.webapp import api_core
    data, status = api_core._start_conversation(payload["phone"], payload["complaint"], payload["product_id"])
    return {"data": data, "status": status}
