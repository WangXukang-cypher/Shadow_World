#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
cd backend
uv sync --group dev
uv run ruff check .
uv run pytest -q
uv run python scripts/export_openapi.py openapi.json
cd ../frontend
if [ ! -d node_modules ]; then npm install; fi
npm run generate:api
npm run typecheck
npm run lint
npm run test
npm run build
