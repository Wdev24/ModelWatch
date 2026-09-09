import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class DriftRunStatus(str, enum.Enum):
    completed = "completed"
    empty = "empty"  # explicit state: window had no observations at all
    failed = "failed"


class TriggeredBy(str, enum.Enum):
    manual = "manual"
    scheduled = "scheduled"


class DriftRun(Base):
    """
    One execution of the drift engine over a window of production data for
    a model version, against one immutable reference snapshot. The window
    itself never overlaps a previous run for the same model version (see
    app.services.drift_service for the windowing policy).
    """
    __tablename__ = "drift_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reference_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[DriftRunStatus] = mapped_column(Enum(DriftRunStatus, name="drift_run_status"), nullable=False)
    threshold_config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    triggered_by: Mapped[TriggeredBy] = mapped_column(Enum(TriggeredBy, name="triggered_by"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    feature_results: Mapped[list["FeatureDriftResult"]] = relationship(
        back_populates="drift_run", cascade="all, delete-orphan"
    )
