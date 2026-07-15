"""FastAPI application entrypoint for the AIVOA AI-First CRM backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.llm import _resolve_model
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.db.session import init_db
from app.routes import chat, followups, history, interactions, recommendations

configure_logging()
logger = get_logger(__name__)

# Bump this string whenever a meaningful backend fix ships. If GET /health
# doesn't show this exact marker, the browser/frontend is NOT talking to
# this copy of the code - stop debugging application logic and go find the
# process/URL that actually IS answering requests instead (a zombie
# `uvicorn` still running on the port, a different deployed backend, etc).
BUILD_MARKER = "2026-07-10-groq-self-heal-v2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_banner = (
        f"\n{'=' * 70}\n"
        f"  AIVOA backend starting | BUILD_MARKER={BUILD_MARKER}\n"
        f"  Groq model  : raw='{settings.GROQ_MODEL}' -> resolved='{_resolve_model(settings.GROQ_MODEL)}'\n"
        f"  Groq fallback: raw='{settings.GROQ_FALLBACK_MODEL}' -> resolved='{_resolve_model(settings.GROQ_FALLBACK_MODEL)}'\n"
        f"  GROQ_API_KEY set: {bool(settings.GROQ_API_KEY)} (len={len(settings.GROQ_API_KEY)})\n"
        f"  Database    : {settings.redacted_database_url}\n"
        f"{'=' * 70}"
    )
    # print() as well as logger.info(): guarantees visibility even if a
    # terminal/tool is suppressing INFO-level logs.
    print(startup_banner)
    logger.info(startup_banner)
    init_db()
    logger.info("Database ready at %s", settings.redacted_database_url)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-First CRM - Healthcare Professional (HCP) Module. The Interaction Details form is "
        "populated exclusively through natural-language conversation with the LangGraph-orchestrated "
        "AI Assistant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/", tags=["system"])
def root() -> dict:
    """Not a real endpoint - just avoids a confusing 404 if someone opens the
    backend URL directly in a browser. The actual app lives on the frontend
    origin; this backend is API-only."""
    return {"message": f"{settings.APP_NAME} API. See /docs for the interactive API reference."}


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV, "build_marker": BUILD_MARKER}


@app.get("/debug/groq-config", tags=["system"])
def debug_groq_config() -> dict:
    """Diagnostic-only endpoint: proves exactly what this running process sees.

    Open this URL directly in a browser (e.g. http://localhost:8000/debug/groq-config)
    while reproducing the issue. If the numbers here don't match what you expect,
    the fix is in your environment/process, not in the application code.
    Never returns the actual API key - only whether one is present.
    """
    return {
        "build_marker": BUILD_MARKER,
        "groq_model_raw": settings.GROQ_MODEL,
        "groq_model_resolved": _resolve_model(settings.GROQ_MODEL),
        "groq_fallback_raw": settings.GROQ_FALLBACK_MODEL,
        "groq_fallback_resolved": _resolve_model(settings.GROQ_FALLBACK_MODEL),
        "groq_api_key_present": bool(settings.GROQ_API_KEY),
        "groq_api_key_length": len(settings.GROQ_API_KEY),
        "database_url_redacted": settings.redacted_database_url,
        "app_env": settings.APP_ENV,
    }


@app.get("/debug/db-health", tags=["system"])
def debug_db_health() -> dict:
    """Diagnostic-only endpoint: proves the app can actually reach the database.

    Open http://localhost:8000/debug/db-health directly in a browser after
    switching DATABASE_URL to MySQL/Postgres. Runs a real `SELECT 1` against
    the configured engine and reports the dialect, redacted connection
    target, and pool stats. Never returns the DB password.
    """
    from sqlalchemy import text

    from app.db.session import engine

    result = {
        "database_url_redacted": settings.redacted_database_url,
        "dialect": engine.dialect.name,
        "driver": engine.dialect.driver,
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["connection_status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint, surface the raw error
        result["connection_status"] = "failed"
        result["error"] = str(exc)

    pool = engine.pool
    result["pool"] = {
        "size": getattr(pool, "size", lambda: None)(),
        "checked_out": getattr(pool, "checkedout", lambda: None)(),
    }
    return result


api_prefix = settings.API_V1_PREFIX
app.include_router(chat.router, prefix=api_prefix)
app.include_router(interactions.router, prefix=api_prefix)
app.include_router(history.router, prefix=api_prefix)
app.include_router(followups.router, prefix=api_prefix)
app.include_router(recommendations.router, prefix=api_prefix)
