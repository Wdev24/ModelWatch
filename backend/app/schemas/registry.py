import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.feature import FeatureDataType


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class ModelVersionCreate(BaseModel):
    version_label: str = Field(min_length=1, max_length=100)


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_id: uuid.UUID
    version_label: str
    created_at: datetime


class FeatureCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    data_type: FeatureDataType


class FeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_version_id: uuid.UUID
    name: str
    data_type: FeatureDataType
    created_at: datetime
