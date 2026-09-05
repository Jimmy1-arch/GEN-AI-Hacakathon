import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from src.database import init_db
from src.triage import triage_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("TriageAI starting up — initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
    yield
    logger.info("TriageAI shutting down.")


app = FastAPI(
    title="TriageAI",
    description="Rule-grounded intake support for human clinical teams",
    lifespan=lifespan
)

# Health check — must respond immediately, no LLM calls
@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok", "service": "TriageAI", "port": 8000})

# Mount API routes
app.include_router(triage_router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
