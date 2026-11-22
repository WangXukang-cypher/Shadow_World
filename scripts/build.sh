#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
cd backend
uv sync --group dev
uv run python scripts/export_openapi.py openapi.json
cd ../frontend
if [ ! -d node_modules ]; then npm install; fi
npm run generate:api
npm run build
cd ../backend
uv run alembic upgrade head
