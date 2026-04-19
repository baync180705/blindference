from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import Settings, get_settings
from db.mongo import close_database, ensure_indexes, get_database, get_in_memory_database, ping_database
from models.response_models import HealthResponse
from routers.admin import router as admin_router
from routers.coverage import router as coverage_router
from routers.disputes import router as disputes_router
from routers.inference import router as inference_router
from routers.models import router as models_router
from routers.nodes import router as nodes_router
from routers.operators import router as operators_router
from services import ServiceContainer
from services.chain_service import ChainService
from services.coverage_service import CoverageService
from services.model_registry_service import ModelRegistryService
from services.node_selector import NodeSelector
from services.quorum_service import QuorumService
from services.verdict_aggregator import VerdictAggregator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blindference.icl")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = await get_database(resolved_settings)
        mongo_connected = await ping_database(database)
        if mongo_connected:
            await ensure_indexes(database)
        else:
            logger.warning("MongoDB unavailable, falling back to in-memory persistence for local development")
            database = get_in_memory_database()
            await ensure_indexes(database)

        chain_service = ChainService(resolved_settings, database)
        node_selector = NodeSelector(chain_service)
        verdict_aggregator = VerdictAggregator()
        coverage_service = CoverageService()
        model_registry_service = ModelRegistryService(database)
        await model_registry_service.ensure_default_models()
        quorum_service = QuorumService(
            database,
            chain_service,
            node_selector,
            verdict_aggregator,
        )

        app.state.settings = resolved_settings
        app.state.mongo_connected = mongo_connected
        app.state.services = ServiceContainer(
            settings=resolved_settings,
            database=database,
            chain_service=chain_service,
            node_selector=node_selector,
            verdict_aggregator=verdict_aggregator,
            coverage_service=coverage_service,
            model_registry_service=model_registry_service,
            quorum_service=quorum_service,
        )

        logger.info("Blindference ICL started")
        try:
            yield
        finally:
            await close_database()
            logger.info("Blindference ICL stopped")

    app = FastAPI(
        title="Blindference ICL",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "%s %s status=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    app.include_router(inference_router)
    app.include_router(nodes_router)
    app.include_router(models_router)
    app.include_router(coverage_router)
    app.include_router(disputes_router)
    app.include_router(admin_router)
    app.include_router(operators_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Blindference Wave 2 ICL is running"}

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        services: ServiceContainer = app.state.services
        return HealthResponse(
            status="ok",
            chain_connected=await services.chain_service.is_connected(),
            mongo_connected=bool(app.state.mongo_connected),
        )

    return app


app = create_app()
