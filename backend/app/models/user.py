from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover - circular import guard
    from .todo import Todo


class ShareMode(str, Enum):  # type: ignore[misc]
    PRIVATE = "private"
    PUBLIC_VIEW = "public_view"
    PUBLIC_EDIT = "public_edit"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    public_slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    share_mode: Mapped[ShareMode] = mapped_column(
        Enum(ShareMode), default=ShareMode.PRIVATE, nullable=False
    )
    edit_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    todos: Mapped[list[Todo]] = relationship(back_populates="user", cascade="all, delete-orphan")
