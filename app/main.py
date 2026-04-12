import asyncio
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timezone

from .settings import settings
from .store import SessionStore, HistoryStore
from .llm import _chat_completion_sync
from .code_runner import run_code
from .tools import (
    search_codeforces_by_code_or_name,
    list_codeforces_by_topics,
    random_codeforces_problem,
    fetch_codeforces_problem_detail,
)
from .problem_import_store import (
    save_problem as save_imported_problem,
    exists as imported_exists,
    load_latest_problem,
    load_problem,
)
from state import default_state, State
from graph import build_graph
from agents.common import ModelRegistry

app = FastAPI(title="LangGraph CP Assistant - Demo")

# Allow CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://codeforces.com",
        "https://www.codeforces.com",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_input: str
    code: str | None = None
    session_id: str | None = None
    user_data: dict | None = None


class ProblemSearchRequest(BaseModel):
    query: str
    limit: int = 10


class TopicProblemRequest(BaseModel):
    topics: list[str]
    limit: int = 20
    min_rating: int | None = None
    max_rating: int | None = None


class RandomProblemRequest(BaseModel):
    user_data: dict | None = None
    topics: list[str] | None = None
    min_rating: int | None = None
    max_rating: int | None = None


class ProblemDetailRequest(BaseModel):
    contest_id: int
    index: str
    cftool_workdir: str | None = None
    cftool_bin: str | None = None
    force_refresh: bool = False


class ImportedExample(BaseModel):
    input: str
    output: str


class RunTestCase(BaseModel):
    id: int
    input: str = ""
    expected: str = ""


class CodeRunRequest(BaseModel):
    language: str
    code: str
    test_cases: list[RunTestCase]
    timeout_seconds: int = 2


class ImportProblemRequest(BaseModel):
    id: str
    platform: str = "codeforces"
    title: str
    time_limit: str = ""
    memory_limit: str = ""
    statement: str = ""
    constraints: str = ""
    input: str = ""
    output: str = ""
    examples: list[ImportedExample] = []
    source_url: str
    tags: list[str] = []
    rating: int | None = None
    created_at: str | None = None


@app.on_event("startup")
async def startup_event():
    model_diag = {
        "api_key_configured": bool(settings.OXLO_API_KEY),
        "calls": 0,
        "success": 0,
        "failure": 0,
        "last_error": "",
        "last_model": "",
    }

    def _model_call(model_name: str, prompt: str, state: State) -> str:
        _ = state
        model_diag["calls"] += 1
        model_diag["last_model"] = model_name
        if not settings.OXLO_API_KEY:
            model_diag["failure"] += 1
            model_diag["last_error"] = "OXLO_API_KEY not configured"
            return ""
        try:
            response = _chat_completion_sync(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a competitive programming assistant model."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
            )
            model_diag["success"] += 1
            model_diag["last_error"] = ""
            return response
        except Exception as error:
            model_diag["failure"] += 1
            model_diag["last_error"] = str(error)
            return ""

    node_models = {
        "orchestrator": ModelRegistry(
            intent_model=lambda prompt, state: _model_call(settings.MODEL_INTENT_DETECTION, prompt, state),
        ),
        "code_analyzer": ModelRegistry(
            code_model=lambda prompt, state: _model_call(settings.MODEL_CODE_ANALYZER, prompt, state),
        ),
        "approach_detection": ModelRegistry(
            reasoning_model=lambda prompt, state: _model_call(settings.MODEL_APPROACH_DETECTOR, prompt, state),
        ),
        "approach_validator": ModelRegistry(
            reasoning_model=lambda prompt, state: _model_call(settings.MODEL_APPROACH_VALIDATOR, prompt, state),
        ),
        "hint_agent": ModelRegistry(
            reasoning_model=lambda prompt, state: _model_call(settings.MODEL_HINT_AGENT, prompt, state),
        ),
        "strategy_agent": ModelRegistry(
            reasoning_model=lambda prompt, state: _model_call(settings.MODEL_STRATEGY_AGENT, prompt, state),
        ),
    }

    g = build_graph(models=ModelRegistry(reasoning_model=lambda prompt, state: _model_call(settings.MODEL_GENERAL_CHAT, prompt, state)), node_models=node_models)

    # attach to app state
    app.state.graph = g
    app.state.model_diagnostics = model_diag

    # stores
    session_store = SessionStore(settings.REDIS_URL, settings.SESSION_TTL_SECONDS)
    try:
        await session_store.connect()
    except Exception:
        # fallback to in-memory if Redis unavailable
        pass

    history_store = HistoryStore(settings.DATABASE_URL)
    history_store.init_db()

    app.state.session_store = session_store
    app.state.history_store = history_store


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())

    session_store: SessionStore = app.state.session_store
    history_store: HistoryStore = app.state.history_store

    state: State = default_state(req.user_input, req.code)
    if req.user_data and isinstance(req.user_data, dict):
        incoming_context = req.user_data.get("problem_context")
        if isinstance(incoming_context, dict):
            state["problem_context"] = {
                "title": str(incoming_context.get("title", "")),
                "statement": str(incoming_context.get("statement", "")),
                "constraints": str(incoming_context.get("constraints", "")),
            }

    # load prior session context (best-effort)
    prior = await session_store.get(session_id)
    recent_turns = history_store.get_recent_turns(session_id=session_id, limit=4)
    state["memory_notes"] = [
        f"User: {(turn.get('user_input') or '')[:90]} | Coach: {(turn.get('final_response') or '')[:90]}"
        for turn in recent_turns
        if isinstance(turn, dict)
    ]

    if isinstance(prior, dict):
        previous_context = prior.get("problem_context")
        if isinstance(previous_context, dict):
            if not state.get("problem_context", {}).get("title"):
                state["problem_context"] = previous_context
        for key in ["expected_approach", "detected_approach", "strategy", "hints", "trainer_profile", "coaching_goal"]:
            if key in prior and not state.get(key):
                state[key] = prior[key]
        old_notes = prior.get("memory_notes")
        if isinstance(old_notes, list):
            state["memory_notes"] = [*old_notes[-4:], *state.get("memory_notes", [])][-8:]

    # run graph (compiled LangGraph invoke is sync)
    g = app.state.graph
    out = await asyncio.to_thread(g.invoke, state)

    out["model_usage"] = dict(getattr(app.state, "model_diagnostics", {}))

    # persist current state
    encoded_state = jsonable_encoder(out)
    await session_store.set(session_id, encoded_state)
    history_store.add_turn(
        session_id=session_id,
        user_input=req.user_input,
        code=req.code,
        final_response=out.get("final_response", ""),
        state=encoded_state,
    )

    return {
        "session_id": session_id,
        "final_response": out.get("final_response"),
        "model_usage": out.get("model_usage", {}),
        "state": encoded_state,
        "recent_history": history_store.get_recent_turns(session_id=session_id, limit=3),
    }


@app.get("/api/debug/model-map")
async def debug_model_map():
    return {
        "api_key_configured": bool(settings.OXLO_API_KEY),
        "models": {
            "orchestrator": settings.MODEL_INTENT_DETECTION,
            "code_analyzer": settings.MODEL_CODE_ANALYZER,
            "approach_detection": settings.MODEL_APPROACH_DETECTOR,
            "approach_validator": settings.MODEL_APPROACH_VALIDATOR,
            "hint_agent": settings.MODEL_HINT_AGENT,
            "strategy_agent": settings.MODEL_STRATEGY_AGENT,
            "response_aggregator": settings.MODEL_GENERAL_CHAT,
        },
        "diagnostics": getattr(app.state, "model_diagnostics", {}),
    }


@app.post("/api/problems/search")
async def search_problems(req: ProblemSearchRequest):
    results = await search_codeforces_by_code_or_name(req.query, limit=req.limit)
    return {
        "query": req.query,
        "count": len(results),
        "items": results,
    }


@app.post("/api/problems/topics")
async def topic_problems(req: TopicProblemRequest):
    results = await list_codeforces_by_topics(
        topics=req.topics,
        limit=req.limit,
        min_rating=req.min_rating,
        max_rating=req.max_rating,
    )
    return {
        "topics": req.topics,
        "count": len(results),
        "items": results,
    }


@app.post("/api/problems/random")
async def random_problem(req: RandomProblemRequest):
    item = await random_codeforces_problem(
        user_data=req.user_data,
        fallback_topics=req.topics,
        min_rating=req.min_rating,
        max_rating=req.max_rating,
    )
    return {
        "item": item,
    }


@app.post("/api/problems/detail")
async def problem_detail(req: ProblemDetailRequest):
    item = await fetch_codeforces_problem_detail(
        req.contest_id,
        req.index,
        cftool_workdir=req.cftool_workdir,
        cftool_bin=req.cftool_bin,
        force_refresh=req.force_refresh,
    )
    return {
        "item": item,
    }


@app.post("/api/problems/import")
async def import_problem(req: ImportProblemRequest):
    problem_id = req.id.strip().replace("-", "_")
    if not problem_id:
        raise HTTPException(status_code=400, detail="Invalid problem id")

    if imported_exists(problem_id):
        raise HTTPException(status_code=409, detail="Problem already imported")

    payload = req.model_dump()
    payload["id"] = problem_id
    payload["platform"] = "codeforces"
    payload["created_at"] = payload.get("created_at") or datetime.now(timezone.utc).isoformat()
    saved = save_imported_problem(payload)
    return {"item": saved}


@app.get("/api/problems/import/{problem_id}")
async def get_imported_problem(problem_id: str):
    normalized = problem_id.strip().replace("-", "_")
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid problem id")
    return {"item": load_problem(normalized)}


@app.get("/api/problems/import/latest")
async def latest_imported_problem():
    item = load_latest_problem()
    return {"item": item}


@app.post("/api/code/run")
async def code_run(req: CodeRunRequest):
    result = await asyncio.to_thread(
        run_code,
        req.language,
        req.code,
        [case.model_dump() for case in req.test_cases],
        max(1, min(req.timeout_seconds, 8)),
    )
    return result
