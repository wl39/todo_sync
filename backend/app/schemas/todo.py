from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from ..models.todo import TodoStatus


class TodoBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str]
    todo_local_date: date = Field(alias="todo_date")

    class Config:
        populate_by_name = True


class TodoCreateRequest(TodoBase):
    pass


class TodoUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str]
    todo_local_date: Optional[date] = Field(None, alias="todo_date")
    status: Optional[TodoStatus]
    version: int

    class Config:
        populate_by_name = True


class TodoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    todo_local_date: date = Field(alias="todo_date")
    status: TodoStatus
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class TodoSummary(BaseModel):
    todo_local_date: date = Field(alias="todo_date")
    count: int

    class Config:
        populate_by_name = True
