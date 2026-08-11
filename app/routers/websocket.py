from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select
from app.services.user_service import get_user_by_email
from app.models.user import User
from app.services.connectionmanager import manager
from app.database import get_session
from app.auth import decode_access_token
from fastapi.concurrency import run_in_threadpool

router = APIRouter()


async def handle_message(user_id: int, message: str):
    print(f"User {user_id} sent: {message}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    payload = decode_access_token(token)

    if not payload:
        await websocket.close(code=1008)
        return

    email = payload.get("sub")

    if not email:
        await websocket.close(code=1008)
        return

    user= await run_in_threadpool(get_user_by_email, email)
        

    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(user.id, websocket)

    try:
        while True:
            message = await websocket.receive_text()

            await handle_message(user.id, message)

    except WebSocketDisconnect:
        manager.disconnect(user.id)