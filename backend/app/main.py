from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models import Search
from app.routers import health, properties, searches


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with SessionLocal() as session:
        await session.execute(
            update(Search)
            .where(Search.status == "scraping")
            .values(status="failed", error_message="Server restarted mid-scrape")
        )
        await session.commit()
    yield


app = FastAPI(title="House Finder API", lifespan=lifespan)

allowed_origins = [o.strip() for o in settings.frontend_url.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(searches.router)
app.include_router(properties.router)
