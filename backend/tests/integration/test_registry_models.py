import pytest
from sqlalchemy.exc import IntegrityError

from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.user import User


def make_user(db_session, email="reg@example.com") -> User:
    user = User(email=email, hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    return user


def test_model_name_unique_per_user(db_session):
    user = make_user(db_session)
    db_session.add(Model(user_id=user.id, name="fraud-model"))
    db_session.flush()

    db_session.add(Model(user_id=user.id, name="fraud-model"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_model_name_can_repeat_across_users(db_session):
    user_a = make_user(db_session, "a@example.com")
    user_b = make_user(db_session, "b@example.com")

    db_session.add(Model(user_id=user_a.id, name="shared-name"))
    db_session.flush()
    db_session.add(Model(user_id=user_b.id, name="shared-name"))
    db_session.flush()  # should not raise


def test_version_label_unique_per_model(db_session):
    user = make_user(db_session, "verowner@example.com")
    model = Model(user_id=user.id, name="m1")
    db_session.add(model)
    db_session.flush()

    db_session.add(ModelVersion(model_id=model.id, version_label="v1"))
    db_session.flush()

    db_session.add(ModelVersion(model_id=model.id, version_label="v1"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_feature_name_unique_per_version(db_session):
    user = make_user(db_session, "featowner@example.com")
    model = Model(user_id=user.id, name="m2")
    db_session.add(model)
    db_session.flush()
    version = ModelVersion(model_id=model.id, version_label="v1")
    db_session.add(version)
    db_session.flush()

    db_session.add(Feature(model_version_id=version.id, name="age", data_type=FeatureDataType.numeric))
    db_session.flush()

    db_session.add(
        Feature(model_version_id=version.id, name="age", data_type=FeatureDataType.categorical)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_model_cascades_to_versions_and_features(db_session):
    user = make_user(db_session, "cascadeowner@example.com")
    model = Model(user_id=user.id, name="m3")
    db_session.add(model)
    db_session.flush()
    version = ModelVersion(model_id=model.id, version_label="v1")
    db_session.add(version)
    db_session.flush()
    feature = Feature(model_version_id=version.id, name="amount", data_type=FeatureDataType.numeric)
    db_session.add(feature)
    db_session.flush()

    db_session.delete(model)
    db_session.flush()

    assert db_session.query(ModelVersion).filter_by(id=version.id).first() is None
    assert db_session.query(Feature).filter_by(id=feature.id).first() is None
