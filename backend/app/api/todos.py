from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db
from ..events.bus import ws_manager
from ..models.user import User
from ..schemas import todo as todo_schema
from ..services.todo import TodoService

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[todo_schema.TodoResponse])
async def list_todos(
    target_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TodoService(db)
    todos = service.list_for_date(current_user.id, target_date)
    return todos


@router.post("", response_model=todo_schema.TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: todo_schema.TodoCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TodoService(db)
    todo = service.create(current_user.id, payload.model_dump(by_alias=False))
    message = {"type": "todo_created", "payload": todo_schema.TodoResponse.model_validate(todo).model_dump()}
    channel = f"user:{current_user.id}"
    await ws_manager.publish(channel, message)
    return todo


@router.patch("/{todo_id}", response_model=todo_schema.TodoResponse)
async def update_todo(
    todo_id: int,
    payload: todo_schema.TodoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TodoService(db)
    data = payload.model_dump(exclude_unset=True, by_alias=False)
    version = data.pop("version", None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version is required")
    todo = service.update(current_user.id, todo_id, data, version)
    message = {"type": "todo_updated", "payload": todo_schema.TodoResponse.model_validate(todo).model_dump()}
    channel = f"user:{current_user.id}"
    await ws_manager.publish(channel, message)
    return todo


@router.post("/{todo_id}/toggle", response_model=todo_schema.TodoResponse)
async def toggle_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TodoService(db)
    todo = service.toggle_status(current_user.id, todo_id)
    message = {
        "type": "todo_toggled",
        "payload": todo_schema.TodoResponse.model_validate(todo).model_dump(),
    }
    channel = f"user:{current_user.id}"
    await ws_manager.publish(channel, message)
    return todo


@router.get("/summary/month", response_model=list[todo_schema.TodoSummary])
async def monthly_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    year, month_value = map(int, month.split("-"))
    first_day = date(year, month_value, 1)
    if month_value == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month_value + 1, 1)
    last_day = next_month - timedelta(days=1)
    service = TodoService(db)
    summary = service.monthly_summary(current_user.id, first_day, last_day)
    return [todo_schema.TodoSummary(todo_date=item[0], count=item[1]) for item in summary]
