#!/usr/bin/env bash
# Starts a local single-node OpenSearch container -- no AWS account,
# no cloud OpenSearch Service, just the real open-source engine running
# on this machine. Security plugin disabled: local dev only, never do
# this for anything reachable off localhost.
set -euo pipefail

if docker ps --format '{{.Names}}' | grep -q '^aftercare-opensearch$'; then
  echo "aftercare-opensearch is already running."
  exit 0
fi

if docker ps -a --format '{{.Names}}' | grep -q '^aftercare-opensearch$'; then
  docker start aftercare-opensearch
else
  docker run -d --name aftercare-opensearch \
    -p 9200:9200 -p 9600:9600 \
    -e "discovery.type=single-node" \
    -e "DISABLE_SECURITY_PLUGIN=true" \
    -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
    opensearchproject/opensearch:2
fi

echo "Waiting for OpenSearch to come up..."
until curl -s http://localhost:9200 >/dev/null 2>&1; do sleep 2; done
echo "OpenSearch is up at http://localhost:9200"
