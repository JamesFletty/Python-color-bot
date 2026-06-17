"""Thin FastAPI wrapper over the Phase 1 SQLite formula engine."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import FormulaRequest, HealthResponse
from src.formula_engine_service import http_status_for_formula, run_formula_engine
from src.paths import DEFAULT_DB_PATH

app = FastAPI(
    title="Hair Color Formula Engine",
    description="HTTP wrapper over formula_engine.py (SQLite + Stage 13 rules).",
    version="0.1.0",
)


def _db_path() -> Path:
    return Path(os.environ.get("FORMULA_DB_PATH", DEFAULT_DB_PATH))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db = _db_path()
    ready = db.exists()
    return HealthResponse(
        status="ok" if ready else "degraded",
        database_path=str(db),
        database_ready=ready,
    )


@app.post("/formula")
def build_formula_endpoint(body: FormulaRequest):
    """Build a formula from shade reference and hair condition parameters."""
    try:
        formula = run_formula_engine(body.to_engine_request(db_path=_db_path()))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    status_code = http_status_for_formula(formula)
    return JSONResponse(status_code=status_code, content=formula)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
