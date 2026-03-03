from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class CodexResult:
    exit_code: int
    events: List[Dict[str, Any]]
    stdout_text: str
    stderr_text: str
    timed_out: bool
    json_parse_errors: int
    command: List[str]


def run_codex_exec(
    prompt: str,
    *,
    cwd: Optional[str] = None,
    timeout_s: int = 180,
    env: Optional[Dict[str, str]] = None,
    codex_bin: str = "codex",
    extra_args: Optional[Sequence[str]] = None,
    max_stdout_chars: int = 2_000_000,
    max_stderr_chars: int = 200_000,
) -> CodexResult:
    """
    Run codex in non-interactive JSON mode and parse JSONL events from stdout.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    cmd = [codex_bin, "exec", "--json", *(extra_args or []), prompt]
    completed = subprocess.run(
        cmd,
        cwd=cwd or os.getcwd(),
        env=os.environ | (env or {}),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    stdout_text = (completed.stdout or "")[-max_stdout_chars:]
    stderr_text = (completed.stderr or "")[-max_stderr_chars:]
    events = [json.loads(line) for line in stdout_text.splitlines() if line.strip()]

    return CodexResult(
        exit_code=completed.returncode,
        events=events,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        timed_out=False,
        json_parse_errors=0,
        command=cmd,
    )


def extract_final_text(events: Sequence[Dict[str, Any]]) -> Optional[str]:
    """
    Best-effort final text extraction from a Codex JSON event stream.
    """
    for event in reversed(list(events)):
        event_type = event.get("type")
        if event_type == "item.completed":
            item = event.get("item") or {}
            if item.get("type") in {"agent_message", "message"} and item.get("text"):
                return item["text"]

        output_text = event.get("output_text")
        if output_text:
            return output_text

        response = event.get("response") or {}
        response_output_text = response.get("output_text")
        if response_output_text:
            return response_output_text

        chunks = [
            content_item["text"]
            for item in response.get("output", [])
            for content_item in item.get("content", [])
            if content_item.get("text")
        ]
        if chunks:
            return "\n".join(chunks)

    return None
