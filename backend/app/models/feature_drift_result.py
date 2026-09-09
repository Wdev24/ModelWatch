import uuid

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.drift.engine import FeatureStatus


class FeatureDriftResult(Base):
    __tablename__ = "feature_drift_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drift_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drift_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True
    )

    rows_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_missing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_invalid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_unseen_category: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_usable: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_status: Mapped[FeatureStatus] = mapped_column(
        Enum(FeatureStatus, name="feature_status"), nullable=False
    )

    drift_run: Mapped["DriftRun"] = relationship(back_populates="feature_results")
    metrics: Mapped[list["FeatureDriftMetric"]] = relationship(
        back_populates="feature_result", cascade="all, delete-orphan"
    )
