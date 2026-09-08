import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.api_key import ApiKey
from app.models.user import User


def make_user(email="a@example.com") -> User:
    return User(email=email, hashed_password="hashed")


def test_create_user(db_session):
    user = make_user()
    db_session.add(user)
    db_session.flush()
    assert user.id is not None
    assert user.created_at is not None


def test_user_email_must_be_unique(db_session):
    db_session.add(make_user("dup@example.com"))
    db_session.flush()

    db_session.add(make_user("dup@example.com"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_api_key_belongs_to_user_and_cascades(db_session):
    user = make_user("owner@example.com")
    db_session.add(user)
    db_session.flush()

    key = ApiKey(user_id=user.id, key_hash="hash123", key_prefix="mw_ab12cd")
    db_session.add(key)
    db_session.flush()

    assert key.is_active is True
    assert key in user.api_keys

    db_session.delete(user)
    db_session.flush()
    remaining = db_session.query(ApiKey).filter_by(id=key.id).first()
    assert remaining is None  # cascaded on user delete


def test_api_key_hash_must_be_unique(db_session):
    user = make_user("owner2@example.com")
    db_session.add(user)
    db_session.flush()

    db_session.add(ApiKey(user_id=user.id, key_hash="samehash", key_prefix="mw_1"))
    db_session.flush()

    db_session.add(ApiKey(user_id=user.id, key_hash="samehash", key_prefix="mw_2"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_api_key_requires_existing_user(db_session):
    orphan_key = ApiKey(user_id=uuid.uuid4(), key_hash="orphanhash", key_prefix="mw_x")
    db_session.add(orphan_key)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_revoked_api_key_is_not_active(db_session):
    from datetime import datetime, timezone

    user = make_user("owner3@example.com")
    db_session.add(user)
    db_session.flush()

    key = ApiKey(user_id=user.id, key_hash="hash456", key_prefix="mw_rev")
    db_session.add(key)
    db_session.flush()
    assert key.is_active is True

    key.revoked_at = datetime.now(timezone.utc)
    db_session.flush()
    assert key.is_active is False
