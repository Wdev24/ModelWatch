import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DriftRunCreate(BaseModel):
    reference_snapshot_id: uuid.UUID | None = None
    window_end: datetime | None = None


class FeatureDriftMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_name: str
    metric_value: float
    p_value: float | None
    threshold_used: float
    status: str


class FeatureDriftResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    feature_id: uuid.UUID
    rows_received: int
    n_valid: int
    n_missing: int
    n_invalid: int
    n_unseen_category: int
    n_usable: int
    feature_status: str
    metrics: list[FeatureDriftMetricOut] = []


class DriftRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_version_id: uuid.UUID
    reference_snapshot_id: uuid.UUID
    window_start: datetime
    window_end: datetime
    status: str
    threshold_config_snapshot: dict
    triggered_by: str
    created_at: datetime


class DriftRunDetailOut(DriftRunOut):
    overall_status: str = "pending"
    feature_results: list[FeatureDriftResultOut] = []
