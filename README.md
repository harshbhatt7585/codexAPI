# Codex Exec JSON Wrapper (Python)

This project exposes `codex exec --json` through a small Python interface and FastAPI endpoint.

## What it does

- Runs Codex in non-interactive mode (`codex exec --json <prompt>`).
- Parses JSONL events from `stdout` (best effort).
- Creates a fresh temporary workspace per API request.
- Returns structured event data and a best-effort final assistant text.

## Files

- `codex_runner.py`: subprocess runner + JSONL parsing.
- `app.py`: FastAPI service.

## Requirements

- Python 3.10+
- Codex CLI installed and authenticated in the environment where this runs.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Run API

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Run Codex:

```bash
curl -X POST http://localhost:8000/codex \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write hello world in Python","timeout_s":120}'
```

## Notes

- This implementation returns full event streams by default (`include_events=true`).
- For safer deployment, run this service inside an isolated container with strict CPU/memory/time limits and restricted filesystem/network access.
