"""
These tests exercise the real Redis queue and a real RQ SimpleWorker, so
they need data actually committed to modelwatch_test (a worker executing
via a separate connection cannot see another session's uncommitted
savepoint data). They use their own committing session instead of the
rollback-per-test fixture used elsewhere, and monkeypatch the worker
module's SessionLocal to point at the same test database.
"""
import uuid as uuid_module

import pytest
from rq import SimpleWorker
from rq.timeouts import TimerDeathPenalty
class WindowsSimpleWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.workers.tasks as tasks_module
from app.drift.engine import FeatureStatus
from app.models.drift_run import DriftRunStatus
from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.monitoring_job import MonitoringJob, MonitoringJobStatus
from app.models.user import User
from app.schemas.reference import FeatureUpload
from app.services.monitoring_job_service import enqueue_monitoring_job
from app.services.reference_service import create_reference_snapshot
from app.workers.queue import monitoring_queue

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/modelwatch_test"
_engine = create_engine(TEST_DATABASE_URL, future=True)
_RealSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def real_db(monkeypatch):
    monkeypatch.setattr(tasks_module, "SessionLocal", _RealSessionLocal)
    session = _RealSessionLocal()
    yield session
    session.close()


def _setup(real_db, email_prefix):
    unique_email = f"{email_prefix}-{uuid_module.uuid4().hex[:8]}@example.com"
    user = User(email=unique_email, hashed_password="hashed")
    real_db.add(user)
    real_db.flush()
    model = Model(user_id=user.id, name=f"m-{unique_email}")
    real_db.add(model)
    real_db.flush()
    version = ModelVersion(model_id=model.id, version_label="v1")
    real_db.add(version)
    real_db.flush()
    feature = Feature(model_version_id=version.id, name="amount", data_type=FeatureDataType.numeric)
    real_db.add(feature)
    real_db.flush()
    real_db.commit()
    return user, version, feature


def test_enqueued_job_runs_via_worker_and_completes(real_db):
    user, version, feature = _setup(real_db, "job1")
    create_reference_snapshot(
        real_db, user, version.id, label="baseline",
        feature_uploads=[FeatureUpload(feature_id=feature.id, numeric_values=[float(i) for i in range(40)])],
    )
    real_db.commit()

    job = enqueue_monitoring_job(real_db, user, version.id)

    worker = WindowsSimpleWorker([monitoring_queue], connection=monitoring_queue.connection)
    worker.work(burst=True)

    real_db.expire_all()
    refreshed = real_db.get(MonitoringJob, job.id)
    assert refreshed.status == MonitoringJobStatus.completed
    assert refreshed.drift_run_id is not None
    assert refreshed.started_at is not None
    assert refreshed.finished_at is not None


def test_completed_job_is_idempotent_on_rerun(real_db):
    user, version, feature = _setup(real_db, "job2")
    create_reference_snapshot(
        real_db, user, version.id, label="baseline",
        feature_uploads=[FeatureUpload(feature_id=feature.id, numeric_values=[float(i) for i in range(40)])],
    )
    real_db.commit()

    job = enqueue_monitoring_job(real_db, user, version.id)
    worker = WindowsSimpleWorker([monitoring_queue], connection=monitoring_queue.connection)
    worker.work(burst=True)

    real_db.expire_all()
    first_drift_run_id = real_db.get(MonitoringJob, job.id).drift_run_id

    # Manually re-invoke the task function directly (simulating RQ redelivery
    # of the same job id after it already succeeded).
    tasks_module.execute_monitoring_job(str(job.id))

    real_db.expire_all()
    refreshed = real_db.get(MonitoringJob, job.id)
    assert refreshed.drift_run_id == first_drift_run_id  # unchanged - no duplicate run


def test_job_for_missing_reference_snapshot_marks_failed(real_db):
    user, version, feature = _setup(real_db, "job3")
    # No reference snapshot created for this version.
    job = enqueue_monitoring_job(real_db, user, version.id)

    worker = WindowsSimpleWorker([monitoring_queue], connection=monitoring_queue.connection)
    worker.work(burst=True)

    real_db.expire_all()
    refreshed = real_db.get(MonitoringJob, job.id)
    assert refreshed.status == MonitoringJobStatus.failed
    assert refreshed.error_message is not None
