from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db
from ..schemas import sharing as sharing_schema
from ..services.auth import AuthService

router = APIRouter(prefix="/sharing", tags=["sharing"])


@router.put("", response_model=sharing_schema.SharingResponse)
async def update_sharing(
    payload: sharing_schema.SharingUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = AuthService(db)
    updated_user = service.update_sharing(
        current_user,
        payload.share_mode,
        payload.public_slug,
        payload.edit_token,
    )
    return sharing_schema.SharingResponse.model_validate(updated_user)
