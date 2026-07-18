"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from uuid import uuid4

from app.config import load_settings
from app.infrastructure.database import dispose_engine
from app.infrastructure.logging import setup_logging, get_logger, set_trace_id
from app.domain.exceptions import CareFlowException
from app.api.health import router as health_router

logger = get_logger(__name__)


async def handle_domain_exception(request, exc: CareFlowException):
    trace_id = getattr(request.state, "trace_id", str(uuid4()))
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "trace_id": trace_id,
            }
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")
    yield
    logger.info("Application shutting down...")
    await dispose_engine()


def create_app() -> FastAPI:
    settings = load_settings()
    setup_logging(level=settings.app.log_level)

    app = FastAPI(
        title="CareFlow AI",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(CareFlowException, handle_domain_exception)

    @app.middleware("http")
    async def trace_id_middleware(request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid4()))
        set_trace_id(trace_id)
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    app.include_router(health_router)
    return app


app = create_app()
