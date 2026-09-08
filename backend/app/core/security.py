"""
Password hashing and API key generation/verification.

API keys: we generate a random secret, store only its SHA-256 hash, and
also store a short non-secret prefix so a key can be identified/listed in
the UI without ever re-displaying the secret. The full plaintext key is
returned to the caller exactly once, at creation time.
"""
import hashlib
import secrets

from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_KEY_PREFIX_TAG = "mw"


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_api_key(plain_key: str) -> str:
    """Deterministic hash so we can look up a key by its hash for auth checks."""
    return hashlib.sha256(plain_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """
    Returns (plaintext_key, key_prefix, key_hash).

    plaintext_key is shown to the caller once and never stored.
    """
    settings = get_settings()
    secret = secrets.token_urlsafe(32)
    plaintext_key = f"{_KEY_PREFIX_TAG}_{secret}"
    key_prefix = plaintext_key[: settings.api_key_prefix_length + len(_KEY_PREFIX_TAG) + 1]
    key_hash = hash_api_key(plaintext_key)
    return plaintext_key, key_prefix, key_hash
