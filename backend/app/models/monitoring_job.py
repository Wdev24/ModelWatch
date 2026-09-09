import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class MonitoringJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class MonitoringJob(Base):
    """
    One enqueued unit of work that executes a drift check via RQ. Manual
    and scheduled triggers both create one of these and enqueue the same
    worker task (spec section 13), so there is one execution path.

    `schedule_id` has no FK yet — MonitoringSchedule doesn't exist until
    M9. The FK constraint is added there; the column is nullable UUID for
    now, populated only by scheduled runs.

    `drift_run_id` is not in the original domain model list but is a
    reasonable, documented V1 addition: without it, a client polling job
    status would have no way to find the DriftRun a completed job
    produced without a separate time-based query.
    """
    __tablename__ = "monitoring_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    drift_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drift_runs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[MonitoringJobStatus] = mapped_column(
        Enum(MonitoringJobStatus, name="monitoring_job_status"), nullable=False, default=MonitoringJobStatus.pending
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
