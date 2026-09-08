from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import authenticate_by_api_key

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    api_key: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),
) -> User:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it in the X-API-Key header.",
        )
    user = authenticate_by_api_key(db, api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
    return user
