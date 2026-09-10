from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.workers.job_worker import job_connection_manager

router = APIRouter(tags=["websockets"])

@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    await job_connection_manager.connect(job_id, websocket)
    try:
        while True:
            # Keep socket alive and listen for client pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        job_connection_manager.disconnect(job_id, websocket)
