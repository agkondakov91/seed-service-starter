import psycopg
import structlog
from fastapi import FastAPI, HTTPException, Request

from config import settings

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    )
    return response


@app.get("/")
def read_root():
    return {"message": settings.greeting}


@app.get("/health")
def liveness():
    return {"status": "alive"}


@app.get("/ready")
def readiness():
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        logger.warning("readiness_failed", reason="database_unavailable")
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}
