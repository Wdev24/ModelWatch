import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class ApiKeyCreateResponse(BaseModel):
    """Returned only once, at creation time — the plaintext key is never stored or shown again."""
    id: uuid.UUID
    api_key: str
    key_prefix: str
    created_at: datetime


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key_prefix: str
    created_at: datetime
    revoked_at: datetime | None


class SignupResponse(BaseModel):
    user: UserOut
    api_key: ApiKeyCreateResponse
