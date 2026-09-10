from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.photos import router as photos_router
from app.api.v1.characters import router as characters_router
from app.api.v1.stories import router as stories_router
from app.api.v1.chats import router as chats_router
from app.api.v1.snapplus import router as snapplus_router
from app.api.v1.library import router as library_router
from app.api.v1.pins import router as pins_router
from app.api.v1.explore import router as explore_router
from app.api.v1.snapfacts import router as snapfacts_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.profile import router as profile_router
from app.api.v1.health import router as health_router
from app.api.v1.websockets import router as ws_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(photos_router)
api_v1_router.include_router(characters_router)
api_v1_router.include_router(stories_router)
api_v1_router.include_router(chats_router)
api_v1_router.include_router(snapplus_router)
api_v1_router.include_router(library_router)
api_v1_router.include_router(pins_router)
api_v1_router.include_router(explore_router)
api_v1_router.include_router(snapfacts_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(ws_router)
