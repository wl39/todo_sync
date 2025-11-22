from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .todo import Todo, TodoStatus


class TodoAuditAction(str, Enum):  # type: ignore[misc]
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    TOGGLE = "TOGGLE"
    DELETE = "DELETE"


class TodoAudit(Base):
    __tablename__ = "todo_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    todo_id: Mapped[int] = mapped_column(ForeignKey("todos.id"), nullable=False, index=True)
    action: Mapped[TodoAuditAction] = mapped_column(Enum(TodoAuditAction), nullable=False)
    from_status: Mapped[Optional[TodoStatus]] = mapped_column(Enum(TodoStatus))
    to_status: Mapped[Optional[TodoStatus]] = mapped_column(Enum(TodoStatus))
    editor_user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    editor_ip: Mapped[Optional[str]] = mapped_column(String(64))
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    todo: Mapped[Todo] = relationship(back_populates="audits")
