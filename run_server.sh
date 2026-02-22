#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
APP_MODULE="${APP_MODULE:-app:app}"

if ! command -v codex >/dev/null 2>&1; then
  echo "Error: codex CLI is not installed or not on PATH." >&2
  exit 1
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "Error: uvicorn is not installed or not on PATH." >&2
  exit 1
fi

echo "Checking Codex authentication..."
if codex login status >/dev/null 2>&1; then
  echo "Codex is already authenticated."
else
  echo "Codex is not authenticated. Running 'codex login'..."
  codex login

  if ! codex login status >/dev/null 2>&1; then
    echo "Error: Codex authentication failed. Please run 'codex login' manually." >&2
    exit 1
  fi
fi

echo "Starting server: ${APP_MODULE} on ${HOST}:${PORT}"
exec uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" "$@"
