from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from fastapi.encoders import jsonable_encoder

from .models import init_state, CPAssistantState, HintItem, ProblemContext, StrategyResult
from .graph import StateGraph
import app.nodes as nodes
from .settings import settings
from .store import SessionStore, HistoryStore

app = FastAPI(title="LangGraph CP Assistant - Demo")

# Allow CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_input: str
    code: str | None = None
    session_id: str | None = None


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
    g.add_edge("hint_agent", "response_aggregator")
    g.add_edge("strategy_agent", "response_aggregator")
    g.add_edge("approach_validator", "response_aggregator")
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

    state: CPAssistantState = init_state(req.user_input, req.code)

    # load prior session context (best-effort)
    prior = await session_store.get(session_id)
    if prior:
        for key in ["problem_context", "expected_approach", "strategy", "hints"]:
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
