from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .user import User

if TYPE_CHECKING:  # pragma: no cover - circular import guard
    from .todo_audit import TodoAudit


class TodoStatus(str, Enum):  # type: ignore[misc]
    PENDING = "PENDING"
    DONE = "DONE"
    PARTIAL = "PARTIAL"


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    todo_local_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    status: Mapped[TodoStatus] = mapped_column(
        Enum(TodoStatus), default=TodoStatus.PENDING, nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="todos")
    audits: Mapped[list[TodoAudit]] = relationship(back_populates="todo", cascade="all, delete-orphan")
