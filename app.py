from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from codex_runner import extract_final_text, run_codex_exec

DEFAULT_CODEX_ARGS = [
    "--skip-git-repo-check",
    "--sandbox",
    "workspace-write",
]
DEFAULT_PROMPT_PREFIX = (
    "You are a friendly assistant. Only plan and answer users' questions. "
    "Do not create any files."
)
PROMPT_PREFIX = os.environ.get("CODEX_PROMPT_PREFIX", DEFAULT_PROMPT_PREFIX).strip()


class CodexRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    timeout_s: int = Field(default=600, ge=1, le=1800)
    include_events: bool = Field(default=True)
    include_raw_output: bool = Field(default=False)
    extra_args: List[str] = Field(default_factory=list)


class CodexSuccessResponse(BaseModel):
    exit_code: int
    final_text: Optional[str]
    events: Optional[List[Dict[str, Any]]] = None
    stdout_text: Optional[str] = None
    stderr_text: Optional[str] = None
    json_parse_errors: int


app = FastAPI(title="Codex Exec API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _build_prompt(prompt: str) -> str:
    if not PROMPT_PREFIX:
        return prompt
    return f"{PROMPT_PREFIX}\n\nUser request:\n{prompt}"


def _run_request(req: CodexRequest, workdir: str) -> CodexSuccessResponse:
    codex_args = [*DEFAULT_CODEX_ARGS, *req.extra_args]

    result = run_codex_exec(
        _build_prompt(req.prompt),
        cwd=workdir,
        timeout_s=req.timeout_s,
        extra_args=codex_args,
    )

    if result.timed_out:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "codex exec timed out",
                "exit_code": result.exit_code,
                "timeout_s": req.timeout_s,
                "command": result.command,
                "stderr_tail": result.stderr_text[-4000:],
            },
        )

    if result.exit_code != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "codex exec failed",
                "exit_code": result.exit_code,
                "command": result.command,
                "stderr_tail": result.stderr_text[-4000:],
                "stdout_tail": result.stdout_text[-4000:],
            },
        )

    return CodexSuccessResponse(
        exit_code=result.exit_code,
        final_text=extract_final_text(result.events),
        events=result.events if req.include_events else None,
        stdout_text=result.stdout_text if req.include_raw_output else None,
        stderr_text=result.stderr_text if req.include_raw_output else None,
        json_parse_errors=result.json_parse_errors,
    )


@app.post("/codex/response/", response_model=CodexSuccessResponse)
def codex_response(req: CodexRequest) -> CodexSuccessResponse:
    # One request = one isolated temporary workspace.
    with tempfile.TemporaryDirectory(prefix="codex_sandbox_") as workdir:
        return _run_request(req, workdir=workdir)
