from datetime import datetime, timedelta, timezone

from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.monitoring_schedule import MonitoringSchedule, ScheduleInterval
from app.models.user import User
from app.services.scheduler_service import deactivate_schedule, find_and_enqueue_due_schedules


def _setup(db_session, email="sched@example.com"):
    user = User(email=email, hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    model = Model(user_id=user.id, name="m")
    db_session.add(model)
    db_session.flush()
    version = ModelVersion(model_id=model.id, version_label="v1")
    db_session.add(version)
    db_session.flush()
    return user, version


def test_schedule_with_no_last_run_is_immediately_due(db_session):
    user, version = _setup(db_session)
    schedule = MonitoringSchedule(model_version_id=version.id, interval=ScheduleInterval.hourly)
    db_session.add(schedule)
    db_session.flush()

    enqueued = find_and_enqueue_due_schedules(db_session, now=datetime.now(timezone.utc))

    assert len(enqueued) == 1
    assert schedule.last_run_at is not None


def test_schedule_not_due_before_interval_elapses(db_session):
    user, version = _setup(db_session, "sched2@example.com")
    now = datetime.now(timezone.utc)
    schedule = MonitoringSchedule(
        model_version_id=version.id, interval=ScheduleInterval.hourly, last_run_at=now
    )
    db_session.add(schedule)
    db_session.flush()

    enqueued = find_and_enqueue_due_schedules(db_session, now=now + timedelta(minutes=30))

    assert enqueued == []


def test_schedule_due_exactly_at_interval_boundary(db_session):
    user, version = _setup(db_session, "sched3@example.com")
    now = datetime.now(timezone.utc)
    schedule = MonitoringSchedule(
        model_version_id=version.id, interval=ScheduleInterval.hourly, last_run_at=now
    )
    db_session.add(schedule)
    db_session.flush()

    enqueued = find_and_enqueue_due_schedules(db_session, now=now + timedelta(hours=1))

    assert len(enqueued) == 1


def test_inactive_schedule_is_never_due(db_session):
    user, version = _setup(db_session, "sched4@example.com")
    schedule = MonitoringSchedule(model_version_id=version.id, interval=ScheduleInterval.hourly, is_active=False)
    db_session.add(schedule)
    db_session.flush()

    enqueued = find_and_enqueue_due_schedules(db_session, now=datetime.now(timezone.utc))

    assert enqueued == []


def test_deactivated_schedule_via_service_stops_being_due(db_session):
    user, version = _setup(db_session, "sched5@example.com")
    schedule = MonitoringSchedule(model_version_id=version.id, interval=ScheduleInterval.daily)
    db_session.add(schedule)
    db_session.flush()

    deactivate_schedule(db_session, user, schedule.id)
    db_session.flush()

    enqueued = find_and_enqueue_due_schedules(db_session, now=datetime.now(timezone.utc))
    assert enqueued == []
