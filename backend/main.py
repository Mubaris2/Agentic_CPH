from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import AnalyzeRequest, AnalyzeResponse, ProgressResponse
from services.agent_orchestrator import AgentOrchestrator
from services.memory_service import MemoryService

app = FastAPI(title="Agentic Competitive Programming Coach")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = AgentOrchestrator()
memory_service = MemoryService()


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "Agentic Competitive Programming Coach"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    result = await orchestrator.run_full_analysis(request.model_dump())
    await memory_service.store_session(result)
    return AnalyzeResponse(**result)


@app.get("/progress", response_model=ProgressResponse)
async def progress() -> ProgressResponse:
    data = await memory_service.get_progress()
    return ProgressResponse(**data)
