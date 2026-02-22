from __future__ import annotations

import tempfile
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from codex_runner import extract_final_text, run_codex_exec


class CodexRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    timeout_s: int = Field(default=180, ge=1, le=1800)
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


@app.post("/codex", response_model=CodexSuccessResponse)
def codex_endpoint(req: CodexRequest) -> CodexSuccessResponse:
    # One request = one isolated temporary workspace.
    with tempfile.TemporaryDirectory(prefix="codex_sandbox_") as workdir:
        result = run_codex_exec(
            req.prompt,
            cwd=workdir,
            timeout_s=req.timeout_s,
            extra_args=req.extra_args,
        )

    if result.timed_out:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "codex exec timed out",
                "exit_code": result.exit_code,
                "stderr_tail": result.stderr_text[-4000:],
            },
        )

    if result.exit_code != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "codex exec failed",
                "exit_code": result.exit_code,
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
