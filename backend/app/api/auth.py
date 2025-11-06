from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db
from ..schemas import auth as auth_schema
from ..services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=auth_schema.UserProfile, status_code=201)
def register(payload: auth_schema.RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.register(payload.email, payload.password, payload.name)
    return user


@router.post("/login", response_model=auth_schema.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(form_data.username, form_data.password)
    token = service.issue_token(user)
    return auth_schema.TokenResponse(access_token=token)


@router.get("/me", response_model=auth_schema.UserProfile)
def me(current_user=Depends(get_current_user)):
    return current_user
