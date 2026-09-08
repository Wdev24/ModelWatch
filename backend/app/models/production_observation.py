import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ObservationStatus(str, enum.Enum):
    valid = "valid"
    missing = "missing"
    invalid = "invalid"
    unseen_category = "unseen_category"


class ProductionObservation(Base):
    """
    One raw production value for one feature. Every observation is kept
    (never silently discarded) with both its raw input and, where
    applicable, its parsed value, plus a status flag so drift/data-quality
    reporting can distinguish valid data from missing/invalid/unseen
    input rather than treating a bad window as silently healthy.
    """
    __tablename__ = "production_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    # Caller-supplied event time, if provided; used for windowing in M9+.
    # Falls back to ingested_at when absent (see ingestion service).
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    raw_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parsed_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    parsed_category: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[ObservationStatus] = mapped_column(
        Enum(ObservationStatus, name="observation_status"), nullable=False
    )
