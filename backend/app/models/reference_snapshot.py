import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ReferenceSnapshot(Base):
    """
    An immutable baseline for a model version. Once created, a snapshot's
    rows (ReferenceStats / ReferenceRawSample / ReferenceRawCategorical)
    are never mutated — a new snapshot is created instead, so every past
    DriftRun stays reproducible against exactly the baseline it used.
    """
    __tablename__ = "reference_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    source_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    model_version: Mapped["ModelVersion"] = relationship()
    stats: Mapped[list["ReferenceStats"]] = relationship(
        back_populates="reference_snapshot", cascade="all, delete-orphan"
    )
