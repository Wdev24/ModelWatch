import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ScheduleInterval(str, enum.Enum):
    """
    A small, fixed set of practical options for V1 (spec section 14) rather
    than a general cron expression parser.
    """
    hourly = "hourly"
    every_6_hours = "every_6_hours"
    daily = "daily"

    def as_timedelta(self):
        from datetime import timedelta
        return {
            ScheduleInterval.hourly: timedelta(hours=1),
            ScheduleInterval.every_6_hours: timedelta(hours=6),
            ScheduleInterval.daily: timedelta(days=1),
        }[self]


class MonitoringSchedule(Base):
    """
    `last_run_at` is not in the original domain model list but is a
    documented, minimal V1 addition: the scheduler needs some persisted
    state to decide whether a schedule is due without depending on
    MonitoringJob history lookups at every tick.
    """
    __tablename__ = "monitoring_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interval: Mapped[ScheduleInterval] = mapped_column(Enum(ScheduleInterval, name="schedule_interval"), nullable=False)
    reference_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reference_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
