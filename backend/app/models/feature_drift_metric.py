import uuid

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.drift.engine import MetricStatus


class FeatureDriftMetric(Base):
    __tablename__ = "feature_drift_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_drift_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_drift_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(20), nullable=False)  # "psi" | "ks" | "js"
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MetricStatus] = mapped_column(Enum(MetricStatus, name="metric_status"), nullable=False)

    feature_result: Mapped["FeatureDriftResult"] = relationship(back_populates="metrics")
