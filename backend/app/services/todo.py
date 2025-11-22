from datetime import date
from typing import Iterable, Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.todo import Todo, TodoStatus
from ..models.todo_audit import TodoAudit, TodoAuditAction


class TodoService:
    def __init__(self, session: Session):
        self.session = session

    def list_for_date(self, user_id: int, target_date: date) -> Sequence[Todo]:
        stmt = (
            select(Todo)
            .where(
                Todo.user_id == user_id,
                Todo.todo_local_date == target_date,
                Todo.is_deleted.is_(False),
            )
            .order_by(Todo.created_at.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def create(self, user_id: int, data: dict) -> Todo:
        todo = Todo(user_id=user_id, **data)
        self.session.add(todo)
        self.session.flush()
        self._audit(todo, TodoAuditAction.CREATE)
        return todo

    def update(self, user_id: int, todo_id: int, data: dict, version: int) -> Todo:
        todo = self._get_owned_todo(user_id, todo_id)
        if todo.version != version:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version mismatch")
        for key, value in data.items():
            setattr(todo, key, value)
        todo.version += 1
        self.session.add(todo)
        self._audit(todo, TodoAuditAction.UPDATE)
        return todo

    def toggle_status(self, user_id: int, todo_id: int) -> Todo:
        todo = self._get_owned_todo(user_id, todo_id)
        next_status = {
            TodoStatus.PENDING: TodoStatus.DONE,
            TodoStatus.DONE: TodoStatus.PARTIAL,
            TodoStatus.PARTIAL: TodoStatus.PENDING,
        }[todo.status]
        previous_status = todo.status
        todo.status = next_status
        todo.version += 1
        self.session.add(todo)
        self._audit(todo, TodoAuditAction.TOGGLE, from_status=previous_status, to_status=next_status)
        return todo

    def monthly_summary(self, user_id: int, first_day: date, last_day: date) -> Iterable[tuple[date, int]]:
        stmt = (
            select(Todo.todo_local_date, func.count(Todo.id))
            .where(
                Todo.user_id == user_id,
                Todo.todo_local_date >= first_day,
                Todo.todo_local_date <= last_day,
                Todo.status.in_([TodoStatus.PENDING, TodoStatus.PARTIAL]),
                Todo.is_deleted.is_(False),
            )
            .group_by(Todo.todo_local_date)
            .order_by(Todo.todo_local_date)
        )
        return [(row[0], row[1]) for row in self.session.execute(stmt).all()]

    def _get_owned_todo(self, user_id: int, todo_id: int) -> Todo:
        todo = self.session.get(Todo, todo_id)
        if not todo or todo.user_id != user_id or todo.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
        return todo

    def _audit(
        self,
        todo: Todo,
        action: TodoAuditAction,
        *,
        from_status: TodoStatus | None = None,
        to_status: TodoStatus | None = None,
        editor_user_id: int | None = None,
        payload: dict | None = None,
    ) -> None:
        audit = TodoAudit(
            todo_id=todo.id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            editor_user_id=editor_user_id,
            payload=payload,
        )
        self.session.add(audit)
