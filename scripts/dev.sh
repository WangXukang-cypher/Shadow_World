#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "未找到 uv。请先安装 uv: https://docs.astral.sh/uv/" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "未找到 npm。请安装 Node.js 24。" >&2
  exit 1
fi
if [ ! -f .env ]; then cp .env.example .env; fi
if grep -q '^SESSION_SECRET=generated-by-dev-script$' .env; then
  if command -v python3 >/dev/null 2>&1; then
    set -- python3
  elif command -v python >/dev/null 2>&1; then
    set -- python
  elif command -v py >/dev/null 2>&1; then
    set -- py -3
  else
    echo "未找到 Python 3。请先安装 Python 3.12+。" >&2
    exit 1
  fi
  secret="$("$@" -c 'import secrets; print(secrets.token_urlsafe(48))')"
  "$@" -c 'from pathlib import Path; import sys; p=Path(".env"); p.write_text(p.read_text(encoding="utf-8").replace("SESSION_SECRET=generated-by-dev-script", "SESSION_SECRET="+sys.argv[1]), encoding="utf-8")' "$secret"
fi
mkdir -p data
(
  cd backend
  uv sync
  uv run alembic upgrade head
  uv run uvicorn app.main:app --reload --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}"
) &
backend_pid=$!
cleanup() { kill "$backend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
cd frontend
if [ ! -d node_modules ]; then npm install; fi
npm run dev -- --host "${FRONTEND_HOST:-127.0.0.1}"
