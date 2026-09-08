import uuid

from sqlalchemy import ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ReferenceStats(Base):
    """
    Precomputed per-feature summary for one snapshot. Numeric features get
    a descriptive summary (count/mean/std/min/max); categorical features
    get category counts. The drift engine (M6) builds PSI/JS bins from the
    raw sample tables, not from this summary — this exists for quick
    display and sanity-checking.
    """
    __tablename__ = "reference_stats"
    __table_args__ = (
        UniqueConstraint(
            "reference_snapshot_id", "feature_id", name="uq_reference_stats_snapshot_feature"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reference_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statistics: Mapped[dict] = mapped_column(JSON, nullable=False)
    n_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_missing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    reference_snapshot: Mapped["ReferenceSnapshot"] = relationship(back_populates="stats")
