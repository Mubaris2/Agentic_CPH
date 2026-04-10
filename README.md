# LangGraph CP Assistant — Minimal Implementation

This repository contains a minimal, runnable scaffold implementing the LangGraph-based agent system described in `LANGGRAPH_AGENT_SYSTEM_ARCHITECTURE.md`.

Quick start (create virtualenv and install):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API:
- `POST /api/chat` JSON {"user_input": "...", "code": "..."}

This demo uses fallbacks for Redis/Postgres: it will attempt to connect if `REDIS_URL`/`DATABASE_URL` are set, otherwise will use in-memory/session-only stores for demo.

Files of interest:
- `app/models.py` — Pydantic state schema
- `app/nodes.py` — node implementations
- `app/graph.py` — simple LangGraph-like runner
- `app/main.py` — FastAPI app and /api/chat endpoint

Frontend (Next.js)
- `web/` contains a minimal Next.js app that talks to the backend at `http://localhost:8000`.

Run backend:

```bash
uvicorn app.main:app --reload
```

Run frontend (from `web/`):

```bash
cd web
npm install
npm run dev
```

Note: models placeholders are left as `<TO_BE_FILLED>` in node metadata to match the architecture spec.
