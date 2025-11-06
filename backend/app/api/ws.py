from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db
from ..events.bus import ws_manager
from ..models.user import User

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/user")
async def user_ws(websocket: WebSocket, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    channel = f"user:{current_user.id}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
