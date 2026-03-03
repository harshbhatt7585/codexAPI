# Codex CLI API

A minimal FastAPI service that executes `codex exec --json` and returns structured results.

## What it does

- Accepts a prompt over HTTP.
- Runs Codex in non-interactive JSON mode.
- Parses JSONL event output from `stdout`.
- Extracts a best-effort `final_text` from events.
- Prepends a default assistant-only instruction so requests stay in planning/Q&A mode and avoid file creation.
- Exposes a single stateless `POST /codex/response/` endpoint.

## Project files

- `app.py`: FastAPI app and HTTP endpoints.
- `codex_runner.py`: subprocess execution, timeout handling, JSONL parsing, and final text extraction.
- `requirements.txt`: runtime dependencies.

## Requirements

- Python 3.10+
- Codex CLI installed and available on `PATH`
- Codex authenticated in the runtime environment

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Login

Authenticate Codex CLI before starting the API:

```bash
codex login
```

## Run locally

```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

Or use the wrapper that checks Codex auth first:

```bash
./run_server.sh
```

Wrapper behavior:

- Runs `codex login status`.
- If not authenticated, runs `codex login`.
- Starts `uvicorn app:app --host 0.0.0.0 --port 8001` by default (`PORT` env var overrides).

Optional overrides:

```bash
HOST=127.0.0.1 PORT=9000 APP_MODULE=app:app ./run_server.sh --reload
```

Prompt behavior:

- Every request is automatically prefixed with: `You are a friendly assistant. Only plan and answer users' questions. Do not create any files.`
- Override that prefix with `CODEX_PROMPT_PREFIX`.
- Set `CODEX_PROMPT_PREFIX` to an empty string to disable prefixing entirely.

## How to use (quickstart)

1. Start the server:

```bash
./run_server.sh
```

2. Set your local API base URL (if server binds to `0.0.0.0:<PORT>`, call it as `127.0.0.1:<PORT>`):

```bash
BASE_URL=http://127.0.0.1:8001
```

3. Verify service is up:

```bash
curl "$BASE_URL/health"
```

4. Send a request:

```bash
curl -X POST "$BASE_URL/codex/response/" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are three ways to reverse a string in Python?",
    "timeout_s": 600,
    "include_events": false
  }'
```

5. If you want client-managed context, include prior turns in the `prompt` you send. The server does not keep conversation state.

## API

### `POST /codex/response/`

Request body:

```json
{
  "prompt": "Explain what a Python decorator is",
  "timeout_s": 600,
  "include_events": true,
  "include_raw_output": false,
  "extra_args": []
}
```

Field notes:

- `prompt` (required): non-empty string.
- `timeout_s`: 1 to 1800 seconds (default `600`).
- `include_events`: include parsed JSON events in response (default `true`).
- `include_raw_output`: include raw `stdout_text`/`stderr_text` (default `false`).
- `extra_args`: additional CLI flags passed to `codex exec --json`.
- The server does not store conversation state. If you need context, send it in the prompt from the client.

By default, the API prepends:

- `--skip-git-repo-check`
- `--sandbox workspace-write`

Example:

```bash
curl -X POST "$BASE_URL/codex/response/" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "System context: We are comparing Python web frameworks.\nUser: What are the tradeoffs between FastAPI and Flask?",
    "timeout_s": 120,
    "include_events": true
  }'
```

Successful response shape:

```json
{
  "exit_code": 0,
  "final_text": "...",
  "events": [],
  "stdout_text": null,
  "stderr_text": null,
  "json_parse_errors": 0
}
```

## Error behavior

- `504`: Codex process timed out.
- `500`: Codex exited non-zero.
- Error responses include `exit_code` and truncated `stdout`/`stderr` tails for debugging.

## Security and deployment notes

- This service executes a local CLI process from user input.
- Run in an isolated environment (container/VM) with strict CPU, memory, filesystem, and network controls.
- Consider authentication/rate limiting before exposing this endpoint outside trusted networks.
