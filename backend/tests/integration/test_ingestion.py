from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.production_observation import ObservationStatus
from app.models.user import User
from app.schemas.ingestion import ObservationIn
from app.schemas.reference import FeatureUpload
from app.services.ingestion_service import UnknownFeatureError, ingest_observations
from app.services.reference_service import create_reference_snapshot
import pytest


def _setup(db_session, email="ingest@example.com"):
    user = User(email=email, hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    model = Model(user_id=user.id, name="m")
    db_session.add(model)
    db_session.flush()
    version = ModelVersion(model_id=model.id, version_label="v1")
    db_session.add(version)
    db_session.flush()
    f_amount = Feature(model_version_id=version.id, name="amount", data_type=FeatureDataType.numeric)
    f_country = Feature(
        model_version_id=version.id, name="country", data_type=FeatureDataType.categorical
    )
    db_session.add_all([f_amount, f_country])
    db_session.flush()
    return user, version, f_amount, f_country


def test_valid_numeric_and_categorical(db_session):
    user, version, f_amount, f_country = _setup(db_session)
    rows = ingest_observations(
        db_session,
        user,
        version.id,
        [
            ObservationIn(feature_id=f_amount.id, raw_value="42.5"),
            ObservationIn(feature_id=f_country.id, raw_value="US"),
        ],
    )
    assert rows[0].status == ObservationStatus.valid
    assert rows[0].parsed_numeric == 42.5
    assert rows[1].status == ObservationStatus.valid
    assert rows[1].parsed_category == "US"


def test_empty_and_missing_values(db_session):
    user, version, f_amount, f_country = _setup(db_session, "missing2@example.com")
    rows = ingest_observations(
        db_session,
        user,
        version.id,
        [
            ObservationIn(feature_id=f_amount.id, raw_value=None),
            ObservationIn(feature_id=f_amount.id, raw_value="   "),
        ],
    )
    assert all(r.status == ObservationStatus.missing for r in rows)


def test_invalid_numeric_value(db_session):
    user, version, f_amount, f_country = _setup(db_session, "invalid@example.com")
    rows = ingest_observations(
        db_session, user, version.id, [ObservationIn(feature_id=f_amount.id, raw_value="not-a-number")]
    )
    assert rows[0].status == ObservationStatus.invalid
    assert rows[0].raw_value == "not-a-number"
    assert rows[0].parsed_numeric is None


def test_unseen_category_detected_against_reference(db_session):
    user, version, f_amount, f_country = _setup(db_session, "unseen@example.com")
    create_reference_snapshot(
        db_session,
        user,
        version.id,
        label="baseline",
        feature_uploads=[FeatureUpload(feature_id=f_country.id, categorical_values=["US", "UK"])],
    )
    db_session.flush()

    rows = ingest_observations(
        db_session, user, version.id, [ObservationIn(feature_id=f_country.id, raw_value="FR")]
    )
    assert rows[0].status == ObservationStatus.unseen_category


def test_category_without_reference_baseline_is_valid(db_session):
    user, version, f_amount, f_country = _setup(db_session, "norefbaseline@example.com")
    rows = ingest_observations(
        db_session, user, version.id, [ObservationIn(feature_id=f_country.id, raw_value="anything")]
    )
    assert rows[0].status == ObservationStatus.valid


def test_unknown_feature_rejected(db_session):
    import uuid

    user, version, f_amount, f_country = _setup(db_session, "unknownfeat@example.com")
    with pytest.raises(UnknownFeatureError):
        ingest_observations(
            db_session, user, version.id, [ObservationIn(feature_id=uuid.uuid4(), raw_value="1")]
        )
