"""Phase 9 - REST API around the pipeline.

Start the server from the project folder (leave this terminal running):
    uv run uvicorn src.api:app --reload

Then open http://127.0.0.1:8000/docs to try every endpoint in the browser, or
import postman/recon-triage.postman_collection.json into Postman.

    GET  /health                    is the server up?
    GET  /exceptions                open exceptions (filter with ?kind=gl_only)
    GET  /exceptions/{id}           the rows behind one exception
    POST /triage                    {"exception_id": "EXC-0027"} -> the agent's answer
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src import agent
from src.common import DATA
from src.tools import get_exception

app = FastAPI(
    title="Reconciliation Break Triage",
    description="Classifies unmatched bank-to-GL items into six break types. "
                "SQL does the matching and all arithmetic; the LLM only classifies and explains.",
    version="1.0",
)


class TriageRequest(BaseModel):
    exception_id: str = Field(examples=["EXC-0027"])


@lru_cache(maxsize=1)
def _exceptions() -> pd.DataFrame:
    return pd.read_csv(DATA / "exceptions.csv", dtype=str).fillna("")


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI
    return OpenAI(max_retries=3, timeout=90)


def _check_id(exception_id: str) -> None:
    if exception_id not in set(_exceptions()["exception_id"]):
        raise HTTPException(status_code=404,
                            detail=f"No exception with id {exception_id}. GET /exceptions lists valid ids.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/exceptions")
def list_exceptions(kind: str | None = Query(None, description="amount_mismatch, bank_only or gl_only"),
                    limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict:
    exc = _exceptions()
    if kind:
        if kind not in ("amount_mismatch", "bank_only", "gl_only"):
            raise HTTPException(status_code=400, detail="kind must be amount_mismatch, bank_only or gl_only.")
        exc = exc[exc["kind"] == kind]
    page = exc.iloc[offset: offset + limit]
    return {"total": len(exc), "offset": offset, "limit": limit,
            "items": [{k: (v or None) for k, v in row.items()} for row in page.to_dict("records")]}


@app.get("/exceptions/{exception_id}")
def exception_detail(exception_id: str) -> dict:
    _check_id(exception_id)
    return get_exception(exception_id)


@app.post("/triage")
def triage(request: TriageRequest) -> dict:
    _check_id(request.exception_id)
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not set in .env, so the agent cannot run.")
    try:
        result = agent.triage(request.exception_id, client=_client())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model call failed: {type(exc).__name__}: {exc}") from exc
    answer = {k: v for k, v in result.items() if k != "steps"}
    answer["tool_steps"] = [{"tool": s["tool"], "arguments": s["arguments"]} for s in result["steps"] if "tool" in s]
    return answer
