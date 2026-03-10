from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import configure_logging
from app.web.home_page import render_home_page

configure_logging()
settings = get_settings()
static_dir = Path(__file__).resolve().parent / "web" / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def home() -> str:
    return render_home_page(settings.api_prefix)


app.include_router(router)
app.include_router(router, prefix=settings.api_prefix)
