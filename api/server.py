"""FastAPI application factory for telint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from telint import storage, monitor, auth
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.init_db()
    await monitor.restore_monitoring_jobs()
    await monitor.start_scheduler()
    yield
    await monitor.stop_scheduler()
    await auth.stop_client()


app = FastAPI(
    title="telint",
    description="Telegram OSINT Scraper API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Serve built frontend if present
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
