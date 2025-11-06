from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.security import create_access_token, hash_password, verify_password
from ..models.user import ShareMode, User

settings = get_settings()


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def register(self, email: str, password: str, name: Optional[str] = None) -> User:
        if self.session.execute(select(User).where(User.email == email)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user = User(email=email, password_hash=hash_password(password), name=name)
        self.session.add(user)
        self.session.flush()
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        user.last_login_at = datetime.now(timezone.utc)
        self.session.add(user)
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(str(user.id))

    def decode_token(self, token: str) -> User:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except JWTError as exc:  # pragma: no cover - external lib validation
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        user = self.session.get(User, int(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
        return user

    def update_sharing(self, user: User, share_mode: ShareMode, public_slug: Optional[str], edit_token: Optional[str]) -> User:
        if share_mode is ShareMode.PRIVATE:
            user.public_slug = None
            user.edit_token = None
        else:
            if not public_slug:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="public_slug is required")
            existing_slug = self.session.execute(
                select(User).where(User.public_slug == public_slug, User.id != user.id)
            ).scalar_one_or_none()
            if existing_slug:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use")
            user.public_slug = public_slug
            if share_mode is ShareMode.PUBLIC_EDIT:
                if not edit_token and not settings.edit_open_unprotected:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="edit_token required")
                user.edit_token = edit_token
            else:
                user.edit_token = None
        user.share_mode = share_mode
        self.session.add(user)
        return user
