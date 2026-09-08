"""
Import all ORM models here so Alembic's autogenerate can see the full
metadata via app.db.base_class.Base. Each new milestone that adds models
must add its import to this file.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
