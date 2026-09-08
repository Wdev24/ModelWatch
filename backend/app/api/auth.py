import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ApiKeyCreateResponse,
    ApiKeyOut,
    SignupRequest,
    SignupResponse,
    UserOut,
)
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    create_user,
    issue_api_key,
    revoke_api_key,
)

router = APIRouter(tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    """
    Creates a user and immediately issues their first API key, since every
    subsequent action requires one. The plaintext key is returned only here.
    """
    try:
        user = create_user(db, payload.email, payload.password)
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    api_key, plaintext_key = issue_api_key(db, user)
    db.commit()
    db.refresh(user)
    db.refresh(api_key)

    return SignupResponse(
        user=UserOut.model_validate(user),
        api_key=ApiKeyCreateResponse(
            id=api_key.id,
            api_key=plaintext_key,
            key_prefix=api_key.key_prefix,
            created_at=api_key.created_at,
        ),
    )


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    api_key, plaintext_key = issue_api_key(db, current_user)
    db.commit()
    db.refresh(api_key)
    return ApiKeyCreateResponse(
        id=api_key.id,
        api_key=plaintext_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(
    api_key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    api_key = revoke_api_key(db, current_user, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    db.commit()
