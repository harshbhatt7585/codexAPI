# Codex CLI API

A minimal stateless FastAPI wrapper around `codex exec --json`.
That means if you have ChatGPT+ subscription you can utilize Codex as an API also without paying for tokens.

## Endpoints

- `GET /health`
- `POST /codex/response/`

`POST /codex/response/` returns a plain JSON response:

```json
{
  "response": "..."
}
```

The server does not keep conversation state. If you want context, send it in the `prompt` from the client.

## Requirements

- Python 3.10+
- Codex CLI installed and available on `PATH`
- Codex authenticated in the runtime environment

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
codex login
```

## Run

Use this bash script which will authenticate the codex and run the server

```bash
./run_server.sh
```

Or directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

## Quickstart

```bash
BASE_URL=http://127.0.0.1:8001

curl "$BASE_URL/health"

curl -X POST "$BASE_URL/codex/response/" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the tradeoffs between FastAPI and Flask?"
  }'
```

## Request Body

Minimal request:

```json
{
  "prompt": "Explain what a Python decorator is"
}
```

Supported fields:

- `prompt`: required
- `timeout_s`: optional, default `600`
- `extra_args`: optional list of extra CLI args
- `include_events`: accepted for compatibility, currently ignored by the response
- `include_raw_output`: accepted for compatibility, currently ignored by the response

The API runs Codex with these default CLI args:

- `--skip-git-repo-check`
- `--sandbox workspace-write`

## Response Body

Successful response:

```json
{
  "response": "FastAPI gives you type-driven validation and automatic docs..."
}
```

## Failure Behavior

This service is intentionally thin. It assumes the happy path.

- If Codex fails, the API can return `500`
- If Codex output is malformed, the API can fail
- There is very little defensive handling by design
