import time

import psycopg
import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from config import settings

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

REQUESTS = Counter(
    "http_requests_total",
    "Всего HTTP-запросов",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Время ответа в секундах",
    ["method", "path"],
)

DB_ERRORS = Counter("db_errors_total", "Ошибки подключения к базе")

app = FastAPI()


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    REQUESTS.labels(request.method, request.url.path, response.status_code).inc()
    LATENCY.labels(request.method, request.url.path).observe(duration)

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
        DB_ERRORS.inc()
        logger.warning("readiness_failed", reason="database_unavailable")
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)