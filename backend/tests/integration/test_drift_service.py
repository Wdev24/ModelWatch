import random
from datetime import datetime, timedelta, timezone

from app.models.drift_run import DriftRunStatus
from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.production_observation import ObservationStatus, ProductionObservation
from app.models.user import User
from app.schemas.reference import FeatureUpload
from app.services.drift_service import run_drift_check
from app.services.reference_service import create_reference_snapshot


def _setup(db_session, email="drift@example.com"):
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


def _make_reference(db_session, user, version, feature, n=50, mean=0.0, seed=1):
    rng = random.Random(seed)
    values = [rng.gauss(mean, 1.0) for _ in range(n)]
    create_reference_snapshot(
        db_session, user, version.id, label="baseline",
        feature_uploads=[FeatureUpload(feature_id=feature.id, numeric_values=values)],
    )
    db_session.flush()


def _insert_observations(db_session, version, feature, n, mean, seed, ingested_at):
    rng = random.Random(seed)
    rows = [
        ProductionObservation(
            model_version_id=version.id,
            feature_id=feature.id,
            ingested_at=ingested_at,
            raw_value=str(rng.gauss(mean, 1.0)),
            parsed_numeric=rng.gauss(mean, 1.0),
            status=ObservationStatus.valid,
        )
        for _ in range(n)
    ]
    db_session.add_all(rows)
    db_session.flush()


def test_empty_window_produces_empty_status(db_session):
    user, version, feature = _setup(db_session)
    _make_reference(db_session, user, version, feature)

    run = run_drift_check(db_session, user, version.id)
    db_session.flush()

    assert run.status == DriftRunStatus.empty
    assert run.feature_results == []


def test_run_with_observations_is_completed(db_session):
    user, version, feature = _setup(db_session, "drift2@example.com")
    _make_reference(db_session, user, version, feature, n=50, mean=0.0, seed=1)
    _insert_observations(db_session, version, feature, n=40, mean=0.0, seed=2, ingested_at=datetime.now(timezone.utc))

    run = run_drift_check(db_session, user, version.id)
    db_session.flush()

    assert run.status == DriftRunStatus.completed
    assert len(run.feature_results) == 1
    assert run.feature_results[0].rows_received == 40


def test_second_run_does_not_reprocess_first_windows_observations(db_session):
    """Boundary test: observations already covered by a prior run's window
    must not reappear in a later run (no double counting)."""
    user, version, feature = _setup(db_session, "drift3@example.com")
    _make_reference(db_session, user, version, feature, n=50, mean=0.0, seed=1)

    now = datetime.now(timezone.utc)
    _insert_observations(db_session, version, feature, n=35, mean=0.0, seed=2, ingested_at=now + timedelta(seconds=1))

    first_run = run_drift_check(db_session, user, version.id, window_end=now + timedelta(seconds=2))
    db_session.flush()
    assert first_run.feature_results[0].rows_received == 35

    # New observations strictly after the first run's window_end.
    later = now + timedelta(seconds=10)
    _insert_observations(db_session, version, feature, n=10, mean=0.0, seed=3, ingested_at=later)

    second_run = run_drift_check(db_session, user, version.id, window_end=later + timedelta(seconds=1))
    db_session.flush()

    assert second_run.window_start == first_run.window_end
    assert len(second_run.feature_results) == 1
    assert second_run.feature_results[0].rows_received == 10  # not 45


def test_observation_exactly_at_window_end_is_included(db_session):
    user, version, feature = _setup(db_session, "drift4@example.com")
    _make_reference(db_session, user, version, feature)

    boundary = datetime.now(timezone.utc)
    _insert_observations(db_session, version, feature, n=1, mean=0.0, seed=5, ingested_at=boundary)

    run = run_drift_check(db_session, user, version.id, window_end=boundary)
    db_session.flush()

    assert run.feature_results[0].rows_received == 1


def test_observation_exactly_at_window_start_is_excluded_from_next_run(db_session):
    user, version, feature = _setup(db_session, "drift5@example.com")
    _make_reference(db_session, user, version, feature)

    boundary = datetime.now(timezone.utc)
    _insert_observations(db_session, version, feature, n=1, mean=0.0, seed=6, ingested_at=boundary)
    first_run = run_drift_check(db_session, user, version.id, window_end=boundary)
    db_session.flush()

    # An observation exactly AT the new window_start (== previous window_end)
    # must not be double-counted in the next run.
    second_run = run_drift_check(db_session, user, version.id, window_end=boundary + timedelta(seconds=10))
    db_session.flush()
    assert second_run.status == DriftRunStatus.empty


def test_insufficient_data_when_no_reference_snapshot_data_for_feature(db_session):
    user, version, feature = _setup(db_session, "drift6@example.com")
    # Reference snapshot exists but has no data for this feature (edge case
    # left for a documented decision): skip creating reference, ingest obs directly.
    now = datetime.now(timezone.utc)
    _insert_observations(db_session, version, feature, n=5, mean=0.0, seed=7, ingested_at=now)

    # Create a snapshot with no feature_uploads at all (feature untouched, no prior snapshot to copy from).
    create_reference_snapshot(db_session, user, version.id, label="empty-baseline", feature_uploads=[])
    db_session.flush()

    run = run_drift_check(db_session, user, version.id, window_end=now)
    db_session.flush()

    assert run.feature_results[0].feature_status.value == "insufficient_data"
