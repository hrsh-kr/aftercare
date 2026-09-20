"""Create the backing resources the Lambdas expect, in the local AWS-stack services.

    DynamoDB Local  the tables template.yaml declares (read from the template itself, so the
                    two cannot drift), including TTL
    OpenSearch      the manual-sections index (English analyzer), the cases and tickets indices,
                    and the seeded history

In a real account CloudFormation creates the tables and you would index once at deploy time; the
Lambdas never create infrastructure at request time.

    .venv/bin/python scripts/bootstrap_local.py
"""
import os
import sys
from pathlib import Path

import boto3
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")
TEMPLATE = Path(__file__).resolve().parent.parent / "template.yaml"


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else None)


def tables_from_template() -> dict[str, dict]:
    doc = yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)
    return {name: r["Properties"] for name, r in doc["Resources"].items() if r["Type"] == "AWS::DynamoDB::Table"}


def dynamodb() -> None:
    client = boto3.client("dynamodb", endpoint_url=ENDPOINT, region_name="ap-south-1", aws_access_key_id="local", aws_secret_access_key="local")
    existing = set(client.list_tables()["TableNames"])
    for logical_id, props in tables_from_template().items():
        ttl = props.get("TimeToLiveSpecification")
        args = {k: props[k] for k in ("BillingMode", "AttributeDefinitions", "KeySchema", "GlobalSecondaryIndexes") if k in props}
        if logical_id not in existing:
            client.create_table(TableName=logical_id, **args)  # table name = logical id, matching `!Ref` under sam local
            client.get_waiter("table_exists").wait(TableName=logical_id)
            print(f"DynamoDB Local: created {logical_id}")
        else:
            print(f"DynamoDB Local: {logical_id} exists")
        if ttl:
            try:
                client.update_time_to_live(TableName=logical_id, TimeToLiveSpecification=ttl)
            except client.exceptions.ClientError:
                pass  # already enabled


def registry() -> None:
    """Load the baseline customer registry (fixtures/sales_data.csv) into DynamoDB. The sandbox demo
    later adds its own order files through POST /api/ingest."""
    os.environ["DYNAMODB_ENDPOINT"] = ENDPOINT
    from src.layer1.catalog import brand_for
    from src.layer1.registration import load_registrations
    from src.storage import get_store
    store = get_store()
    n = 0
    for r in load_registrations():
        store.put_registration({k: getattr(r, k) for k in ("customer_name", "customer_phone", "product_id", "product_name",
                                                         "serial_number", "purchase_date", "retailer", "purchase_price")} | {"source": "baseline"})
        n += 1
    print(f"DynamoDB Local: {n} baseline registrations loaded")


def opensearch() -> None:
    from src.layer1 import opensearch_retrieval as osr
    from src.layer3b import case_index
    osr.ensure_indexed(force=True)
    case_index.reset()
    print(f"OpenSearch: {osr.INDEX_NAME}, {case_index.CASES}, {case_index.TICKETS} ready; history seeded")


if __name__ == "__main__":
    dynamodb()
    registry()
    opensearch()
