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


def _truncate_tail(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _parse_jsonl_events(stdout_text: str) -> tuple[List[Dict[str, Any]], int]:
    events: List[Dict[str, Any]] = []
    parse_errors = 0

    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
        else:
            parse_errors += 1

    return events, parse_errors


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

    if cwd is None:
        cwd = os.getcwd()

    cmd = [codex_bin, "exec", "--json"]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(prompt)

    child_env = os.environ.copy()
    if env:
        child_env.update(env)

    timed_out = False
    stdout_text = ""
    stderr_text = ""
    exit_code = 0

    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        exit_code = completed.returncode
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        timeout_stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        timeout_stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stdout_text = timeout_stdout
        stderr_text = timeout_stderr + f"\nProcess timed out after {timeout_s}s."

    events, parse_errors = _parse_jsonl_events(stdout_text)
    stdout_text = _truncate_tail(stdout_text, max_stdout_chars)
    stderr_text = _truncate_tail(stderr_text, max_stderr_chars)

    return CodexResult(
        exit_code=exit_code,
        events=events,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        timed_out=timed_out,
        json_parse_errors=parse_errors,
        command=cmd,
    )


def extract_final_text(events: Sequence[Dict[str, Any]]) -> Optional[str]:
    """
    Best-effort final text extraction from a Codex JSON event stream.
    """
    for event in reversed(list(events)):
        event_type = event.get("type")
        if event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict):
                item_type = item.get("type")
                item_text = item.get("text")
                if item_type in {"agent_message", "message"} and isinstance(item_text, str) and item_text.strip():
                    return item_text

        output_text = event.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        response = event.get("response")
        if isinstance(response, dict):
            response_output_text = response.get("output_text")
            if isinstance(response_output_text, str) and response_output_text.strip():
                return response_output_text

            output = response.get("output")
            if isinstance(output, list):
                chunks: List[str] = []
                for item in output:
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content")
                    if not isinstance(content, list):
                        continue
                    for content_item in content:
                        if not isinstance(content_item, dict):
                            continue
                        text = content_item.get("text")
                        if isinstance(text, str):
                            chunks.append(text)
                if chunks:
                    joined = "\n".join(chunks).strip()
                    if joined:
                        return joined

    return None
