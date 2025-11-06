from typing import Optional

from pydantic import BaseModel

from ..models.user import ShareMode


class SharingUpdateRequest(BaseModel):
    share_mode: ShareMode
    public_slug: Optional[str]
    edit_token: Optional[str]


class SharingResponse(BaseModel):
    share_mode: ShareMode
    public_slug: Optional[str]
    edit_token: Optional[str]

    class Config:
        from_attributes = True
