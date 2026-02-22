# Codex CLI API

A minimal FastAPI service that executes `codex exec --json` and returns structured results.

## What it does

- Accepts a prompt over HTTP.
- Runs Codex in non-interactive JSON mode.
- Parses JSONL event output from `stdout`.
- Extracts a best-effort `final_text` from events.
- Supports two workspace modes:
  - `POST /codex`: one-shot temporary workspace (deleted after request).
  - `POST /codex/conv`: persistent conversation workspace (reused by `conversation_id`).

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

4. One-shot request (temporary workspace, cleaned after request):

```bash
curl -X POST "$BASE_URL/codex" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to reverse a string",
    "timeout_s": 600,
    "include_events": false
  }'
```

5. Persistent conversation request (workspace reused by `conversation_id`):

```bash
curl -X POST "$BASE_URL/codex/conv" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create notes.txt with line hello",
    "conversation_id": "my-rl-conv",
    "timeout_s": 600,
    "include_events": false
  }'
```

Call `/codex/conv` again with the same `conversation_id` to continue in the same workspace.

## API

### `POST /codex`

Request body:

```json
{
  "prompt": "Write hello world in Python",
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

By default, the API prepends:

- `--skip-git-repo-check`
- `--sandbox workspace-write`

Example:

```bash
curl -X POST "$BASE_URL/codex" \
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

### `POST /codex/conv`

Use this endpoint when you want files to persist between calls.

Request body:

```json
{
  "prompt": "Create train.py",
  "conversation_id": "rl-demo-1",
  "timeout_s": 600,
  "include_events": false,
  "include_raw_output": false,
  "extra_args": []
}
```

Field notes:

- `conversation_id` (optional): if provided, reuses that workspace; if omitted, server creates one.
- Workspace path defaults to `./conversations/<conversation_id>`.
- Override base path with env var `CODEX_CONVERSATION_ROOT`.

Successful response shape:

```json
{
  "exit_code": 0,
  "final_text": "...",
  "events": null,
  "stdout_text": null,
  "stderr_text": null,
  "json_parse_errors": 0,
  "conversation_id": "rl-demo-1",
  "workspace_dir": "/abs/path/to/conversations/rl-demo-1"
}
```

Conversation example:

```bash
curl -X POST "$BASE_URL/codex/conv" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create notes.txt with line hello",
    "conversation_id": "my-rl-conv",
    "timeout_s": 600,
    "include_events": false
  }'
```

## Error behavior

- `504`: Codex process timed out.
- `500`: Codex exited non-zero.
- Error responses include `exit_code` and truncated `stdout`/`stderr` tails for debugging.

## Security and deployment notes

- This service executes a local CLI process from user input.
- Run in an isolated environment (container/VM) with strict CPU, memory, filesystem, and network controls.
- Consider authentication/rate limiting before exposing this endpoint outside trusted networks.
