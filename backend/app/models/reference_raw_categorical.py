import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ReferenceRawCategorical(Base):
    """Raw categorical baseline values for one feature in one snapshot."""
    __tablename__ = "reference_raw_categoricals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reference_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_value: Mapped[str] = mapped_column(String(500), nullable=False)
