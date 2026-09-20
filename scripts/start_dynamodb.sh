#!/usr/bin/env bash
# DynamoDB Local: AWS's own downloadable DynamoDB, no account, no cloud. Note it is not in
# the Build It table (see docs/AWS_FEEDBACK_LOG.md) -- the file store remains the default.
set -euo pipefail
if docker ps --format '{{.Names}}' | grep -q '^aftercare-dynamodb$'; then echo "already running"; exit 0; fi
if docker ps -a --format '{{.Names}}' | grep -q '^aftercare-dynamodb$'; then docker start aftercare-dynamodb
else docker run -d --name aftercare-dynamodb -p 8000:8000 amazon/dynamodb-local -jar DynamoDBLocal.jar -sharedDb -inMemory; fi
echo "DynamoDB Local at http://localhost:8000"
