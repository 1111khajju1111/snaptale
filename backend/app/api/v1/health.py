from fastapi import APIRouter

router = APIRouter(tags=["monitoring"])

@router.get("/health")
async def health_check():
    """
    Lightweight health endpoint for Render & UptimeRobot monitoring.
    Never triggers expensive AI operations or external API requests.
    """
    return {
        "status": "healthy",
        "service": "snaptale-backend",
        "timestamp": "2026-09-10T00:00:00Z"
    }
