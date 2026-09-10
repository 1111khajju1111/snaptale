from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_v1_router
from app.api.v1.health import router as root_health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown / teardown logic
    await engine.dispose()

app = FastAPI(
    title="SnapTale API",
    description="Every Picture Has a Story. No humans. Just everything else.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health check (e.g. GET /health directly for Render & UptimeRobot)
app.include_router(root_health_router)

# Include v1 API
app.include_router(api_v1_router)

@app.get("/")
async def root():
    return {
        "product": "SnapTale",
        "tagline": "Every Picture Has a Story.",
        "supporting_line": "No humans. Just everything else.",
        "docs_url": "/docs"
    }
