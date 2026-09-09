import random
from datetime import datetime, timezone

from app.models.alert import Alert
from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.production_observation import ObservationStatus, ProductionObservation
from app.models.user import User
from app.schemas.reference import FeatureUpload
from app.services.drift_service import run_drift_check
from app.services.reference_service import create_reference_snapshot


def _setup(db_session, email="alert@example.com"):
    user = User(email=email, hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    model = Model(user_id=user.id, name="m")
    db_session.add(model)
    db_session.flush()
    version = ModelVersion(model_id=model.id, version_label="v1")
    db_session.add(version)
    db_session.flush()
    feature = Feature(model_version_id=version.id, name="amount", data_type=FeatureDataType.numeric)
    db_session.add(feature)
    db_session.flush()
    return user, version, feature


def test_drifted_feature_generates_alert(db_session):
    user, version, feature = _setup(db_session)
    rng = random.Random(1)
    ref_values = [rng.gauss(0, 1) for _ in range(50)]
    create_reference_snapshot(
        db_session, user, version.id, label="baseline",
        feature_uploads=[FeatureUpload(feature_id=feature.id, numeric_values=ref_values)],
    )
    db_session.flush()

    now = datetime.now(timezone.utc)
    shifted = [ProductionObservation(
        model_version_id=version.id, feature_id=feature.id, ingested_at=now,
        raw_value="100", parsed_numeric=100.0 + i, status=ObservationStatus.valid,
    ) for i in range(40)]
    db_session.add_all(shifted)
    db_session.flush()

    run = run_drift_check(db_session, user, version.id, window_end=now)
    db_session.flush()

    alerts = db_session.query(Alert).filter(Alert.drift_run_id == run.id).all()
    assert len(alerts) == 1
    assert alerts[0].feature_id == feature.id
    assert alerts[0].severity == "high"


def test_no_drift_generates_no_alert(db_session):
    user, version, feature = _setup(db_session, "alert2@example.com")
    ref_values = [float(i % 40) for i in range(200)]
    create_reference_snapshot(
        db_session, user, version.id, label="baseline",
        feature_uploads=[FeatureUpload(feature_id=feature.id, numeric_values=ref_values)],
    )
    db_session.flush()

    now = datetime.now(timezone.utc)
    same = [ProductionObservation(
        model_version_id=version.id, feature_id=feature.id, ingested_at=now,
        raw_value=str(float(i)), parsed_numeric=float(i), status=ObservationStatus.valid,
    ) for i in range(40)]
    db_session.add_all(same)
    db_session.flush()

    run = run_drift_check(db_session, user, version.id, window_end=now)
    db_session.flush()

    alerts = db_session.query(Alert).filter(Alert.drift_run_id == run.id).all()
    assert alerts == []
