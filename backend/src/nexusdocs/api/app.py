"""FastAPI factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..graph import InMemoryGraphRepository
from ..graph.repository import GraphRepository
from ..llm import build_default_client
from ..llm.client import LLMClient
from .errors import ApiError, ErrorBody, ErrorEnvelope
from .routers import (
    definitions,
    entities,
    fragments,
    ingest,
    meta,
    relationships,
    search,
    views,
)
from .routers import (
    settings as settings_router,
)


def _build_repository(settings: Settings) -> GraphRepository:
    if settings.repository_backend == "neo4j":
        from ..graph.neo4j_repo import Neo4jGraphRepository

        repo = Neo4jGraphRepository(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
    else:
        repo = InMemoryGraphRepository()
    repo.initialize()
    return repo


def build_app(
    *,
    repository: GraphRepository | None = None,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build a FastAPI app. Caller may inject pre-built dependencies (for tests)."""
    settings = settings or get_settings()
    repo = repository or _build_repository(settings)
    llm_client = llm or build_default_client()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.repository = repo
        app.state.llm = llm_client
        app.state.settings = settings
        yield

    app = FastAPI(
        title="NexusDocs API",
        version="0.1.0",
        description="Topology-aware knowledge graph documentation platform.",
        lifespan=lifespan,
    )
    app.state.repository = repo
    app.state.llm = llm_client
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        envelope = exc.envelope.model_dump(mode="json")
        return JSONResponse(envelope, status_code=exc.status_code)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> JSONResponse:
        return JSONResponse(
            ErrorEnvelope(
                error=ErrorBody(code="not_found", message="resource not found")
            ).model_dump(mode="json"),
            status_code=404,
        )

    api = _v1_router()
    api.include_router(entities.router)
    api.include_router(relationships.router)
    api.include_router(fragments.router)
    api.include_router(views.router)
    api.include_router(ingest.router)
    api.include_router(search.router)
    api.include_router(definitions.router)
    api.include_router(settings_router.router)
    api.include_router(meta.router)
    app.include_router(api)

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _v1_router():
    from fastapi import APIRouter

    return APIRouter(prefix="/api/v1")


def default_app() -> FastAPI:
    return build_app()
