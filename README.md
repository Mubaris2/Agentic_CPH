# LangGraph CP Assistant — Minimal Implementation

This repository contains a minimal, runnable scaffold implementing the LangGraph-based agent system described in `LANGGRAPH_AGENT_SYSTEM_ARCHITECTURE.md`.

Quick start (create virtualenv and install):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# optional but recommended for robust Codeforces statement scraping fallback
playwright install chromium
uvicorn app.main:app --reload
```

API:
- `POST /api/chat` JSON {"user_input": "...", "code": "..."}

Problem fetch API:
- `POST /api/problems/search` for question code or name
	- body: `{ "query": "Two Buttons" }` or `{ "query": "520B" }`
- `POST /api/problems/topics` for topic-based list
	- body: `{ "topics": ["dp", "graphs"], "limit": 20, "min_rating": 1200, "max_rating": 1800 }`
- `POST /api/problems/random` for personalized random question
	- body: `{ "user_data": { "preferred_topics": ["dp"], "target_rating": 1500, "solved_problem_codes": ["520B"] } }`
- `POST /api/problems/detail` for exact statement details (description/constraints/examples)
	- body: `{ "contest_id": 2211, "index": "A" }`
- `POST /api/problems/import` to store client-side DOM extracted statement payload
	- body: `{ "id": "734_A", "platform": "codeforces", "title": "...", "time_limit": "...", "memory_limit": "...", "statement": "...", "input": "...", "output": "...", "examples": [{"input": "...", "output": "..."}], "source_url": "..." }`

Modular Codeforces fetcher package:
- `fetcher/cf_api.py` → cached Codeforces metadata (title/tags/rating)
- `fetcher/scraper.py` → async Playwright statement scraping with retries/backoff
- `fetcher/parser.py` → structured parsing (`title`, `time_limit`, `memory_limit`, `statement`, `input`, `output`, `examples`)
- `fetcher/cache.py` → disk JSON cache (`cache/{contest}_{index}.json`)
- `fetcher/main.py` → orchestration + CLI

CLI examples:

```bash
cd fetcher
python main.py 734 A --pretty

# or from project root
python -m fetcher.main 734 A --pretty

# custom cftool setup
python -m fetcher.main 734 A --pretty --cftool-workdir /tmp/cf_workspace --cftool-bin /home/user/go/bin/cftool
```

Two-click import flow (recommended):
- Click 1 in app modal: open the target Codeforces problem URL.
- Click 2 in browser extension popup: `Import Current Problem`.
- Extension scrapes DOM (`title`, limits, statement, input/output specs, samples) and posts to `/api/problems/import`.

Browser extension setup (one-time):
1. Open `chrome://extensions` and enable Developer mode.
2. Click `Load unpacked` and select `extension/codeforces-importer`.
3. Pin `CPH Codeforces Importer` for quick access.
4. In extension popup, keep backend URL as `http://localhost:8000` (or adjust if needed).

cftool integration notes:
- Fetch modal includes optional `cftool` settings (binary path + problem directory)
- You can click `Open Codeforces Login` in the modal to sign in from browser if needed before importing
- `/api/problems/detail` accepts `cftool_workdir`, `cftool_bin`, `force_refresh`

`/api/chat` also accepts optional user profile for random/topic fetch prompts:

```json
{
	"user_input": "Give me a random dp problem",
	"session_id": "optional",
	"user_data": {
		"preferred_topics": ["dp", "graphs"],
		"avoided_topics": ["games"],
		"target_rating": 1500,
		"rating_window": 200,
		"solved_problem_codes": ["520B", "4A"]
	}
}
```

## Model Configuration (Oxlo)

Backend nodes call Oxlo's OpenAI-compatible API using `openai.OpenAI(base_url="https://api.oxlo.ai/v1")`.

Set environment variables before running backend:

```bash
export OXLO_API_KEY="<YOUR_API_KEY>"
export OXLO_BASE_URL="https://api.oxlo.ai/v1"  # optional, default already set
# optional: use proxy if Codeforces blocks your server IP (403/challenge)
export CODEFORCES_PROXY_URL="http://<proxy-host>:<proxy-port>"
```

Agent-to-model mapping used by default:

- Intent Detection → `Llama 3.2 3B`
- Hint Agent → `Llama 3.1 8B`
- Code Analyzer → `Qwen 3 Coder 30B`
- Strategy Agent → `DeepSeek R1 8B`
- Approach Detector → `DeepSeek R1 8B`
- Approach Validator → `DeepSeek R1 8B`
- Counterexample Generator → `DeepSeek R1 8B`
- General Chat / Response Aggregator → `Mistral 7B`

You can override each model via env vars (`MODEL_INTENT_DETECTION`, `MODEL_HINT_AGENT`, etc.).

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
