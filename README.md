# Codex CLI API

A minimal FastAPI service that executes `codex exec --json` and returns structured results.

## What it does

- Accepts a prompt over HTTP.
- Runs Codex in non-interactive JSON mode.
- Parses JSONL event output from `stdout`.
- Extracts a best-effort `final_text` from events.
- Executes each request in its own temporary workspace.

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

## Run locally

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## API

### `POST /codex`

Request body:

```json
{
  "prompt": "Write hello world in Python",
  "timeout_s": 180,
  "include_events": true,
  "include_raw_output": false,
  "extra_args": []
}
```

Field notes:

- `prompt` (required): non-empty string.
- `timeout_s`: 1 to 1800 seconds (default `180`).
- `include_events`: include parsed JSON events in response (default `true`).
- `include_raw_output`: include raw `stdout_text`/`stderr_text` (default `false`).
- `extra_args`: additional CLI flags passed to `codex exec --json`.

Example:

```bash
curl -X POST http://localhost:8000/codex \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a Python function that reverses a string",
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
