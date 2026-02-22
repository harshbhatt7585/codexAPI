from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from codex_runner import extract_final_text, run_codex_exec

DEFAULT_CODEX_ARGS = [
    "--skip-git-repo-check",
    "--sandbox",
    "workspace-write",
]
CONVERSATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DEFAULT_CONVERSATION_ROOT = Path(__file__).resolve().parent / "conversations"
CONVERSATION_ROOT = Path(
    os.environ.get("CODEX_CONVERSATION_ROOT", str(DEFAULT_CONVERSATION_ROOT))
).expanduser().resolve()


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


class CodexConversationRequest(CodexRequest):
    conversation_id: Optional[str] = Field(default=None, min_length=1, max_length=64)


class CodexConversationResponse(CodexSuccessResponse):
    conversation_id: str
    workspace_dir: str


app = FastAPI(title="Codex Exec API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _resolve_conversation_id(raw_conversation_id: Optional[str]) -> str:
    if raw_conversation_id is None:
        return f"conv_{uuid4().hex[:12]}"

    conversation_id = raw_conversation_id.strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail={"error": "conversation_id cannot be empty"})

    if not CONVERSATION_ID_RE.fullmatch(conversation_id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": (
                    "conversation_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ "
                    "(letters, numbers, dot, underscore, dash)"
                )
            },
        )

    return conversation_id


def _conversation_workdir(conversation_id: str) -> Path:
    workdir = (CONVERSATION_ROOT / conversation_id).resolve()
    if CONVERSATION_ROOT != workdir and CONVERSATION_ROOT not in workdir.parents:
        raise HTTPException(status_code=400, detail={"error": "invalid conversation_id path"})
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def _run_request(req: CodexRequest, workdir: str) -> CodexSuccessResponse:
    codex_args = [*DEFAULT_CODEX_ARGS, *req.extra_args]

    result = run_codex_exec(
        req.prompt,
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


@app.post("/codex", response_model=CodexSuccessResponse)
def codex_endpoint(req: CodexRequest) -> CodexSuccessResponse:
    # One request = one isolated temporary workspace.
    with tempfile.TemporaryDirectory(prefix="codex_sandbox_") as workdir:
        return _run_request(req, workdir=workdir)


@app.post("/codex/", response_model=CodexSuccessResponse, include_in_schema=False)
def codex_endpoint_with_slash(req: CodexRequest) -> CodexSuccessResponse:
    return codex_endpoint(req)


@app.post("/codex/conv", response_model=CodexConversationResponse)
def codex_conversation_endpoint(req: CodexConversationRequest) -> CodexConversationResponse:
    conversation_id = _resolve_conversation_id(req.conversation_id)
    workdir = _conversation_workdir(conversation_id)
    result = _run_request(req, workdir=str(workdir))
    return CodexConversationResponse(
        exit_code=result.exit_code,
        final_text=result.final_text,
        events=result.events,
        stdout_text=result.stdout_text,
        stderr_text=result.stderr_text,
        json_parse_errors=result.json_parse_errors,
        conversation_id=conversation_id,
        workspace_dir=str(workdir),
    )


@app.post("/codex/conv/", response_model=CodexConversationResponse, include_in_schema=False)
def codex_conversation_endpoint_with_slash(req: CodexConversationRequest) -> CodexConversationResponse:
    return codex_conversation_endpoint(req)
