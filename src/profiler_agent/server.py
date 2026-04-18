from __future__ import annotations

import uvicorn
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from fastapi import FastAPI

from profiler_agent.a2a.executor import KolbAgentExecutor
from profiler_agent.config import get_settings
from profiler_agent.interview.engine import InterviewEngine
from profiler_agent.interview.repository import InterviewRepository
from profiler_agent.llm.huggingface import HuggingFaceLLM
from profiler_agent.mcp.client import KolbMCPClient


def build_agent_card() -> AgentCard:
    settings = get_settings()
    return AgentCard(
        name="kolb-profiler-agent",
        description="Recupera o construye el perfil Kolb de un alumno mediante A2A y MCP.",
        url=settings.public_base_url,
        version="0.1.0",
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
        skills=[
            AgentSkill(
                id="kolb-profile-retrieval-and-interview",
                name="Kolb Profile Retrieval",
                description="Busca el perfil Kolb del alumno en MCP y, si falta, lo crea con entrevista guiada incremental.",
                tags=["kolb", "a2a", "mcp", "assessment", "langgraph"],
                examples=["id_alumno: 12345"],
                inputModes=["text/plain"],
                outputModes=["text/plain"],
            )
        ],
    )


def create_app() -> FastAPI:
    settings = get_settings()
    llm = HuggingFaceLLM(settings=settings)
    engine = InterviewEngine(llm=llm)
    repository = InterviewRepository()
    mcp_client = KolbMCPClient(settings=settings)
    executor = KolbAgentExecutor(
        engine=engine,
        interview_repository=repository,
        mcp_client=mcp_client,
    )
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    a2a_app = A2AFastAPIApplication(build_agent_card(), handler).build()

    @a2a_app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @a2a_app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "kolb-profiler-agent",
            "a2a_card": f"{settings.public_base_url}/v1/card",
            "health": f"{settings.public_base_url}/healthz",
        }

    return a2a_app


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "profiler_agent.server:create_app",
        host=settings.app_host,
        port=settings.app_port,
        factory=True,
        reload=False,
    )


app = create_app()
