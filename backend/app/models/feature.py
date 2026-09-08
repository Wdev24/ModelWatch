import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class FeatureDataType(str, enum.Enum):
    numeric = "numeric"
    categorical = "categorical"


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("model_version_id", "name", name="uq_features_model_version_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[FeatureDataType] = mapped_column(
        Enum(FeatureDataType, name="feature_data_type"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    model_version: Mapped["ModelVersion"] = relationship(back_populates="features")
