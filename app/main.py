"""FastAPI application factory."""

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.config import load_settings
from app.domain.exceptions import CareFlowException
from app.infrastructure.database import dispose_engine
from app.infrastructure.logging import get_logger, set_trace_id, setup_logging

logger = get_logger(__name__)


async def handle_domain_exception(request: Request, exc: Exception) -> JSONResponse:
    """Convert CareFlowException to the standard error response format."""
    assert isinstance(exc, CareFlowException)
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
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application startup and shutdown lifecycle."""
    logger.info("Application starting...")
    yield
    logger.info("Application shutting down...")
    await dispose_engine()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = load_settings()
    setup_logging(level=settings.app.log_level)

    app = FastAPI(
        title="CareFlow AI",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(CareFlowException, handle_domain_exception)

    @app.middleware("http")
    async def trace_id_middleware(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get("X-Trace-ID", str(uuid4()))
        set_trace_id(trace_id)
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    app.include_router(health_router)
    return app


app = create_app()
