from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.reference_raw_sample import ReferenceRawSample
from app.models.user import User
from app.schemas.reference import FeatureUpload
from app.services.reference_service import create_reference_snapshot


def _setup(db_session, email="snap@example.com"):
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


def test_first_snapshot_stores_uploaded_features_only(db_session):
    user, version, f_amount, f_country = _setup(db_session)

    snapshot = create_reference_snapshot(
        db_session,
        user,
        version.id,
        label="v1-baseline",
        feature_uploads=[
            FeatureUpload(feature_id=f_amount.id, numeric_values=[1.0, 2.0, 3.0]),
        ],
    )
    db_session.flush()

    assert len(snapshot.stats) == 1
    assert snapshot.stats[0].feature_id == f_amount.id
    assert snapshot.stats[0].n_valid == 3


def test_second_snapshot_copies_forward_untouched_feature(db_session):
    user, version, f_amount, f_country = _setup(db_session, "copyforward@example.com")

    snap1 = create_reference_snapshot(
        db_session,
        user,
        version.id,
        label="snap1",
        feature_uploads=[
            FeatureUpload(feature_id=f_amount.id, numeric_values=[1.0, 2.0, 3.0]),
            FeatureUpload(feature_id=f_country.id, categorical_values=["US", "UK"]),
        ],
    )
    db_session.flush()

    # Second snapshot only re-uploads `amount`; `country` should be copied forward.
    snap2 = create_reference_snapshot(
        db_session,
        user,
        version.id,
        label="snap2",
        feature_uploads=[
            FeatureUpload(feature_id=f_amount.id, numeric_values=[10.0, 20.0]),
        ],
    )
    db_session.flush()

    stats_by_feature = {s.feature_id: s for s in snap2.stats}
    assert f_country.id in stats_by_feature
    assert stats_by_feature[f_country.id].statistics["category_counts"] == {"US": 1, "UK": 1}
    assert stats_by_feature[f_amount.id].n_valid == 2

    # The old snapshot's amount data must remain untouched (immutability).
    old_rows = (
        db_session.query(ReferenceRawSample)
        .filter(
            ReferenceRawSample.reference_snapshot_id == snap1.id,
            ReferenceRawSample.feature_id == f_amount.id,
        )
        .all()
    )
    assert sorted(r.value for r in old_rows) == [1.0, 2.0, 3.0]


def test_missing_values_counted_not_discarded(db_session):
    user, version, f_amount, f_country = _setup(db_session, "missing@example.com")

    snapshot = create_reference_snapshot(
        db_session,
        user,
        version.id,
        label="with-missing",
        feature_uploads=[
            FeatureUpload(feature_id=f_amount.id, numeric_values=[1.0, None, 3.0]),
        ],
    )
    db_session.flush()

    stat = snapshot.stats[0]
    assert stat.n_valid == 2
    assert stat.n_missing == 1
