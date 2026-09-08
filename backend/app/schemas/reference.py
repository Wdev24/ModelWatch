import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureUpload(BaseModel):
    feature_id: uuid.UUID
    # Exactly one of these must be populated, matching the feature's data_type;
    # validated against the feature's declared type in the service layer.
    numeric_values: list[float | None] | None = None
    categorical_values: list[str | None] | None = None


class ReferenceSnapshotCreate(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    feature_uploads: list[FeatureUpload] = Field(default_factory=list)
    source_metadata: dict | None = None


class ReferenceStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    feature_id: uuid.UUID
    statistics: dict
    n_valid: int
    n_missing: int


class ReferenceSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_version_id: uuid.UUID
    label: str
    created_at: datetime
    source_metadata: dict | None
    stats: list[ReferenceStatsOut] = []
