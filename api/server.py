"""FastAPI application factory for telint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from telint import storage, monitor, auth
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await storage.init_db()
    await monitor.restore_monitoring_jobs()
    await monitor.start_scheduler()
    yield
    # shutdown
    await monitor.stop_scheduler()
    await auth.stop_client()


app = FastAPI(
    title="telint",
    description="Telegram OSINT Scraper API",
    lifespan=lifespan,
)

app.include_router(router)
