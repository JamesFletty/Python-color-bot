# Hair Color Formula Engine

A professional hair color formula engine and database for salon formula generation, conversion, and multi-brand mapping.

## Overview

This project provides a source-traceable, machine-readable dataset of professional hair color systems (1,840+ shades) with a deterministic rule engine exposed via a FastAPI REST API.

## Architecture

- **FastAPI** REST API (`api/`) — dispatches to SQLite (default) or PostgreSQL backend
- **SQLite backend** (`src/`, `hair_color.db`) — lightweight local Phase 1 implementation
- **PostgreSQL backend** (`hair_color_db/production/`) — full production track
- **Data pipeline** (`hair_color_db/stage01–13/`) — normalized shades, tone maps, formulation rules

## Running the App

The API starts automatically on port 5000 via the "Start application" workflow.

- Health check: `GET /health`
- Build a formula: `POST /formula` with a `FormulaRequest` body
- Production endpoints: `/v1/production/health`, `/v1/production/formula`

## Setup

```bash
# Initialize SQLite database (run once)
python3 init_db.py

# Start API server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 5000 --reload
```

## Environment Variables

- `ENGINE_BACKEND` — `sqlite` (default) or `postgres`
- `DATABASE_URL` — PostgreSQL connection string (required for postgres backend)
- `FORMULA_DB_PATH` — Override SQLite database path

See `.env.example` for reference.

## User Preferences

- Keep existing project structure and conventions
