#!/usr/bin/env bash
# The one way to run Aftercare: everything as AWS Lambda under SAM Local.
#   OpenSearch + DynamoDB Local (containers) -> create tables/indices -> sam build -> sam local start-api
# Needs Docker and Ollama running (the model). Open http://127.0.0.1:3000
set -euo pipefail
cd "$(dirname "$0")/.."
# the model: pull once, then keep it loaded so the first reply isn't a 10-second cold start
MODEL="${AFTERCARE_MODEL:-gemma2:9b}"
if command -v ollama >/dev/null; then
  ollama list 2>/dev/null | grep -q "^${MODEL}" || ollama pull "${MODEL}"
  curl -s -m 60 localhost:11434/api/generate -d "{\"model\":\"${MODEL}\",\"prompt\":\"\",\"keep_alive\":\"2h\"}" >/dev/null 2>&1 &
fi
bash scripts/start_opensearch.sh
bash scripts/start_dynamodb.sh
sleep 2
# inline, not exported: sam local would pass a host-shell value into the Lambda, overriding the
# template's host.docker.internal address (inside the container, localhost is the container)
DYNAMODB_ENDPOINT=http://localhost:8000 .venv/bin/python scripts/bootstrap_local.py
[ "${SKIP_BUILD:-0}" = "1" ] || { bash scripts/stage_lambda.sh; sam build --use-container; }
exec sam local start-api --warm-containers EAGER --static-dir "$PWD/public" --port 3000
