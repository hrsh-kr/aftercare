#!/usr/bin/env bash
# Stage exactly what the Lambda needs into lambda_pkg/ (SAM's CodeUri). `sam build` copies the
# CodeUri folder wholesale, so pointing it at the repo root ships .venv, docs and archives too;
# staging keeps the package to code + fixtures + policies + the arm64 Cedar binary + requirements.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf lambda_pkg && mkdir -p lambda_pkg/tools/cedar
cp -r src fixtures policies lambda_pkg/
cp requirements.txt lambda_pkg/
cp tools/cedar-lambda/cedar lambda_pkg/tools/cedar/cedar
find lambda_pkg -name __pycache__ -type d -prune -exec rm -rf {} +
echo "staged lambda_pkg/ ($(du -sh lambda_pkg | cut -f1) before dependencies)"
