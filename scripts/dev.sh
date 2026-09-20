#!/usr/bin/env bash
# The one way to run Aftercare: everything as AWS Lambda under SAM Local.
#   containers (OpenSearch, DynamoDB Local on Corretto) -> create tables/indices -> sam build -> sam local start-api
# Then open http://127.0.0.1:3000  (landing, /demo, /sandbox, /dashboard).
#   SKIP_BUILD=1 bash scripts/dev.sh     reuse the last `sam build` (static files in public/ are always live)
set -euo pipefail
cd "$(dirname "$0")/.."

fail() { echo "✗ $1" >&2; exit 1; }
[ -x .venv/bin/python ] || fail "no .venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
command -v sam >/dev/null    || fail "AWS SAM CLI not found: brew install aws-sam-cli"
docker info >/dev/null 2>&1  || fail "Docker isn't running (SAM Local, OpenSearch and DynamoDB Local need it)"
[ -x tools/cedar/cedar ] && [ -x tools/cedar-lambda/cedar ] || fail "Cedar CLI missing: bash scripts/install_cedar_cli.sh"
command -v ollama >/dev/null || fail "Ollama not found (the local model): https://ollama.com"
curl -s -m 3 localhost:11434/api/tags >/dev/null || fail "Ollama isn't running: start it with 'ollama serve' in another terminal"

# the model: pull once, then keep it loaded so the first reply isn't a 10-second cold start
MODEL="${AFTERCARE_MODEL:-gemma2:9b}"
ollama list 2>/dev/null | grep -q "^${MODEL}" || ollama pull "${MODEL}"
curl -s -m 60 localhost:11434/api/generate -d "{\"model\":\"${MODEL}\",\"prompt\":\"\",\"keep_alive\":\"2h\"}" >/dev/null 2>&1 &

bash scripts/start_opensearch.sh
bash scripts/start_dynamodb.sh
sleep 2
# inline, not exported: sam local would pass a host-shell value into the Lambda, overriding the
# template's host.docker.internal address (inside the container, localhost is the container)
DYNAMODB_ENDPOINT=http://localhost:8000 .venv/bin/python scripts/bootstrap_local.py
[ "${SKIP_BUILD:-0}" = "1" ] || { bash scripts/stage_lambda.sh; sam build --use-container; }
exec sam local start-api --warm-containers EAGER --static-dir "$PWD/public" --port 3000
