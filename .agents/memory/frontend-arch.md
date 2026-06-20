---
name: Frontend architecture
description: How the React frontend is built and served by FastAPI in this project
---

# Frontend Architecture

**Why:** Single-port Replit setup (port 5000) requires the frontend to be served from FastAPI, not a separate dev server.

**How to apply:**
- Source: `frontend/` (Vite + React + TypeScript + Tailwind v4)
- Build output: `static/dist/` (set in `frontend/vite.config.ts`)
- FastAPI mounts `static/dist/assets` as StaticFiles and has a SPA catch-all route returning `index.html`
- To rebuild after frontend changes: `cd frontend && pnpm build`
- API routes use `/api/` prefix to avoid conflicts with SPA routing
- During dev, `--reload` in uvicorn hot-reloads the Python backend; frontend changes require a manual `pnpm build`

**Key files:**
- `frontend/vite.config.ts` — build outDir is `../static/dist`
- `api/main.py` — mounts static files and SPA fallback at bottom (only if `static/dist` exists)
- `api/catalog.py` — brand/line/shade DB lookups for `/api/brands` and `/api/shades`
- `api/ai_service.py` — xAI (Grok) integration via OpenAI-compatible SDK
- `api/schemas.py` — includes AIFormulaRequest, AITranslateRequest, AIFormulaResponse
