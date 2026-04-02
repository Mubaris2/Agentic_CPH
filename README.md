# Agentic Competitive Programming Coach (MVP)

A modular multi-agent AI coach for competitive programming practice.

## Tech Stack
- Backend: FastAPI + SQLite
- Frontend: Streamlit
- LLM: OpenAI-compatible Chat Completions API via configurable environment variables

## Project Structure

- backend/main.py
- backend/agents/
  - code_analyzer.py
  - complexity_agent.py
  - pattern_agent.py
  - strategy_agent.py
  - hint_agent.py
  - thinking_agent.py
  - evaluation_agent.py
  - summary_agent.py
- backend/services/
  - agent_orchestrator.py
  - memory_service.py
  - scoring_service.py
- backend/models/schemas.py
- backend/db/storage.py
- frontend/app.py

## Environment Variables

Optional (for LLM-powered responses in strategy/hint/thinking/summary agents):

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (default: `https://api.openai.com/v1`)
- `OPENAI_MODEL` (default: `gpt-4o-mini`)

Optional database path:

- `COACH_DB_PATH` (default: `db/coach.db`, relative to backend working directory)

Frontend backend URL:

- `BACKEND_URL` (default: `http://localhost:8000`)

## Run Instructions

Install dependencies from project root:

```bash
pip install -r requirements.txt
```

Run backend:

```bash
cd backend
uvicorn main:app --reload
```

Run frontend (new terminal):

```bash
cd frontend
streamlit run app.py
```

## API

### `POST /analyze`
Input:

```json
{
  "code": "...",
  "problem_description": "...",
  "is_correct": true,
  "used_hints": false
}
```

Output: combined response from all 8 agents.

### `GET /progress`
Returns:
- past scores
- average score
- basic insights

## Notes
- If no API key is configured, agents use deterministic fallback heuristics.
- Session data is stored in SQLite for simple progress tracking.
