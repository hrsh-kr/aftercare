#!/usr/bin/env bash
# DynamoDB Local, run on Amazon Corretto (docker/dynamodb-local/Dockerfile): AWS's own local DynamoDB
# on AWS's own OpenJDK build. No account, no cloud.
set -euo pipefail
cd "$(dirname "$0")/.."
if docker ps --format '{{.Names}}' | grep -q '^aftercare-dynamodb$'; then echo "DynamoDB Local already running"; exit 0; fi
docker rm -f aftercare-dynamodb >/dev/null 2>&1 || true
docker image inspect aftercare-dynamodb-corretto >/dev/null 2>&1 || docker build -q -t aftercare-dynamodb-corretto docker/dynamodb-local
docker run -d --name aftercare-dynamodb -p 8000:8000 aftercare-dynamodb-corretto >/dev/null
echo "DynamoDB Local (Corretto) at http://localhost:8000"
