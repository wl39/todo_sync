from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..events.bus import ws_manager
from ..models.user import ShareMode, User
from ..schemas import todo as todo_schema
from ..services.todo import TodoService

router = APIRouter(prefix="/public", tags=["public"])


def _get_user_by_slug(db: Session, slug: str) -> User:
    user = db.execute(select(User).where(User.public_slug == slug)).scalar_one_or_none()
    if not user or user.share_mode is ShareMode.PRIVATE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not public")
    return user


@router.get("/{slug}/todos", response_model=list[todo_schema.TodoResponse])
async def list_public_todos(
    slug: str,
    target_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    user = _get_user_by_slug(db, slug)
    service = TodoService(db)
    todos = service.list_for_date(user.id, target_date)
    return todos


@router.post("/{slug}/todos/{todo_id}/toggle", response_model=todo_schema.TodoResponse)
async def toggle_public_todo(
    slug: str,
    todo_id: int,
    db: Session = Depends(get_db),
    edit_token: Optional[str] = Query(None),
):
    user = _get_user_by_slug(db, slug)
    if user.share_mode is ShareMode.PUBLIC_VIEW:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editing not allowed")
    if user.share_mode is ShareMode.PUBLIC_EDIT and user.edit_token and user.edit_token != edit_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid edit token")
    service = TodoService(db)
    todo = service.toggle_status(user.id, todo_id)
    message = {
        "type": "todo_toggled",
        "payload": todo_schema.TodoResponse.model_validate(todo).model_dump(),
    }
    channel = f"calendar:{slug}"
    await ws_manager.publish(channel, message)
    user_channel = f"user:{user.id}"
    await ws_manager.publish(user_channel, message)
    return todo


@router.get("/{slug}/summary/month", response_model=list[todo_schema.TodoSummary])
async def public_monthly_summary(
    slug: str,
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
):
    user = _get_user_by_slug(db, slug)
    year, month_value = map(int, month.split("-"))
    first_day = date(year, month_value, 1)
    if month_value == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month_value + 1, 1)
    last_day = next_month - timedelta(days=1)
    service = TodoService(db)
    summary = service.monthly_summary(user.id, first_day, last_day)
    return [todo_schema.TodoSummary(todo_date=item[0], count=item[1]) for item in summary]


@router.websocket("/ws/{slug}")
async def public_ws(websocket: WebSocket, slug: str, db: Session = Depends(get_db)):
    _get_user_by_slug(db, slug)
    channel = f"calendar:{slug}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
