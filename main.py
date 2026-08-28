import psycopg
from fastapi import FastAPI

from config import settings

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": settings.greeting}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("SELECT 1")
    return {"db": "ok"}
