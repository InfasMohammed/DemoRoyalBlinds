"""Application composition, configuration checks, and lifecycle management."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .access import access_settings, require_reviewer
from .api import business, health, knowledge, projects
from .business_data import BusinessDataUnavailable, data_source
from .execution import ApprovalWorker
from .llm import chat_info
from .record_creation import CreationUnavailable
from .store import ReportStore, StorageUnavailable


@asynccontextmanager
async def lifespan(application: FastAPI):
    worker = ApprovalWorker(application.state.report_store)
    enabled = os.getenv("POST_APPROVAL_WORKER_ENABLED", "true").lower() == "true"
    if enabled:
        worker.start()
    try:
        yield
    finally:
        if enabled:
            worker.stop()


async def storage_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def create_app() -> FastAPI:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if os.getenv("DATA_MODE", "demo") != "demo":
        raise RuntimeError(
            "Only DATA_MODE=demo is supported. Connect verified business data in a separate production implementation."
        )
    if os.getenv("KNOWLEDGE_RETRIEVAL_MODE", "local") not in ("local", "supabase_vector"):
        raise RuntimeError("KNOWLEDGE_RETRIEVAL_MODE must be local or supabase_vector.")
    data_source()
    chat_info()
    access = access_settings()
    application = FastAPI(
        title="Royal Blinds · Operations Studio",
        version="0.2.0",
        lifespan=lifespan,
        description="Interview demonstration. Human-reviewed estimates and demo work orders.",
        docs_url=None if access.required else "/docs",
        redoc_url=None if access.required else "/redoc",
        openapi_url=None if access.required else "/openapi.json",
    )
    application.state.access_settings = access
    application.state.report_store = ReportStore()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    for error_type in (BusinessDataUnavailable, StorageUnavailable, CreationUnavailable):
        application.add_exception_handler(error_type, storage_error)
    for routes in (health.router, business.router, knowledge.router, projects.router):
        application.include_router(routes, prefix="/api", dependencies=[Depends(require_reviewer)])
    return application


app = create_app()
