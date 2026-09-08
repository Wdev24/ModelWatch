"""
Auth business logic. Kept separate from the router so it can be tested and
reused without going through HTTP.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key, hash_password
from app.models.api_key import ApiKey
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    pass


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyRegisteredError(email) from exc
    return user


def issue_api_key(db: Session, user: User) -> tuple[ApiKey, str]:
    """Returns (ApiKey row, plaintext_key). The plaintext is never persisted."""
    plaintext_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(user_id=user.id, key_hash=key_hash, key_prefix=key_prefix)
    db.add(api_key)
    db.flush()
    return api_key, plaintext_key


def revoke_api_key(db: Session, user: User, api_key_id) -> ApiKey | None:
    """Revokes the key only if it belongs to the given user. Returns None if not found/owned."""
    from datetime import datetime, timezone

    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.id == api_key_id, ApiKey.user_id == user.id)
        .first()
    )
    if api_key is None:
        return None
    api_key.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return api_key


def authenticate_by_api_key(db: Session, plaintext_key: str) -> User | None:
    """Looks up an active API key by its hash and returns the owning user, or None."""
    key_hash = hash_api_key(plaintext_key)
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
        .first()
    )
    if api_key is None:
        return None
    return api_key.user
