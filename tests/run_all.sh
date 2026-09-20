#!/usr/bin/env bash
# Runs every test module. OpenSearch / DynamoDB Local tests skip themselves if those aren't up.
set -e
cd "$(dirname "$0")/.."
for t in test_escalation test_cedar test_ingest test_channel test_api_robustness test_site_fresh test_case_index test_store_contract; do
  echo "== $t"; .venv/bin/python -m tests.$t
done
