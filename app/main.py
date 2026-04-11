from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timezone

from .models import init_state, CPAssistantState, HintItem, ProblemContext, StrategyResult
from .graph import StateGraph
import app.nodes as nodes
from .settings import settings
from .store import SessionStore, HistoryStore
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
    # build graph
    g = StateGraph()
    # register nodes
    g.add_node("orchestrator", nodes.orchestrator_node)
    g.add_node("debug_fork", nodes.debug_fork_node)
    g.add_node("code_analyzer", nodes.code_analyzer_node)
    g.add_node("approach_detection", nodes.approach_detection_node)
    g.add_node("approach_validator", nodes.approach_validator_node)
    g.add_node("counterexample_gen", nodes.counterexample_gen_node)
    g.add_node("hint_agent", nodes.hint_agent_node)
    g.add_node("strategy_agent", nodes.strategy_agent_node)
    g.add_node("response_aggregator", nodes.response_aggregator_node)
    g.add_node("problem_fetch_tool", nodes.problem_fetch_tool_node)

    # edges
    g.add_edge("START", "orchestrator")
    g.add_conditional_edges("orchestrator", lambda s: s.get("intent", "general"), {
        "hint": "hint_agent",
        "strategy": "strategy_agent",
        "problem_fetch": "problem_fetch_tool",
        "debug": "debug_fork",
        "general": "debug_fork",
    })

    g.add_edge("debug_fork", "strategy_agent")
    g.add_edge("debug_fork", "code_analyzer")
    g.add_edge("code_analyzer", "approach_detection")
    g.add_edge("approach_detection", "approach_validator")
    g.add_conditional_edges("approach_validator", lambda s: "counterexample" if ((s.get("validation_result") or {}).get("trigger_counterexample") if isinstance(s.get("validation_result"), dict) else getattr(s.get("validation_result"), "trigger_counterexample", False)) else "aggregate", {
        "counterexample": "counterexample_gen",
        "aggregate": "response_aggregator",
    })
    g.add_edge("counterexample_gen", "response_aggregator")
    g.add_edge("hint_agent", "response_aggregator")
    g.add_edge("strategy_agent", "response_aggregator")
    g.add_edge("problem_fetch_tool", "orchestrator")
    g.add_edge("response_aggregator", "END")

    # attach to app state
    app.state.graph = g

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

    state: CPAssistantState = init_state(req.user_input, req.code, req.user_data)

    # load prior session context (best-effort)
    prior = await session_store.get(session_id)
    if prior:
        for key in ["problem_context", "problem_candidates", "expected_approach", "strategy", "hints", "counterexample"]:
            current_val = state.get(key)
            if key in prior and (current_val in (None, "", [], {}) or current_val is None):
                val = prior[key]
                if key == "problem_context" and isinstance(val, dict):
                    state[key] = ProblemContext(**val)
                elif key == "strategy" and isinstance(val, dict):
                    state[key] = StrategyResult(**val)
                elif key == "hints" and isinstance(val, list):
                    state[key] = [HintItem(**item) if isinstance(item, dict) else item for item in val]
                else:
                    state[key] = val

    # run graph
    g: StateGraph = app.state.graph
    out = await g.run("START", state)

    # ensure final aggregation if not present
    if not out.get("final_response"):
        # call aggregator
        agg = await nodes.response_aggregator_node(out)
        out.update(agg)

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
        "state": encoded_state,
        "recent_history": history_store.get_recent_turns(session_id=session_id, limit=3),
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
