"""
Import all ORM models here so Alembic's autogenerate can see the full
metadata via app.db.base_class.Base. Each new milestone that adds models
must add its import to this file.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
from app.models.model import Model  # noqa: F401
from app.models.model_version import ModelVersion  # noqa: F401
from app.models.feature import Feature  # noqa: F401
from app.models.reference_snapshot import ReferenceSnapshot  # noqa: F401
from app.models.reference_stats import ReferenceStats  # noqa: F401
from app.models.reference_raw_sample import ReferenceRawSample  # noqa: F401
from app.models.reference_raw_categorical import ReferenceRawCategorical  # noqa: F401
from app.models.production_observation import ProductionObservation  # noqa: F401
from app.models.drift_run import DriftRun  # noqa: F401
from app.models.feature_drift_result import FeatureDriftResult  # noqa: F401
from app.models.feature_drift_metric import FeatureDriftMetric  # noqa: F401
from app.models.monitoring_job import MonitoringJob  # noqa: F401
