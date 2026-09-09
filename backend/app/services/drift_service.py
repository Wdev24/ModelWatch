"""
Drift execution orchestration: the DB/HTTP-facing layer that wraps the
pure app.drift.engine. Manual and scheduled drift checks are both meant
to call `run_drift_check` (spec section 4/13) so there is exactly one
code path that decides windows and persists results.

Windowing policy (spec section 9), fixed and documented for V1:
- A model version's *first* drift run windows from the model version's
  created_at up to `now` (or an explicit `window_end`).
- Every subsequent run windows from the previous run's window_end
  (exclusive) up to the new window_end (inclusive). This guarantees:
    * no observation is double-counted (windows never overlap - each
      run starts exactly where the last one ended)
    * already-processed observations cannot silently reappear
    * model versions are isolated (all queries filter by model_version_id)
    * an empty window is an explicit DriftRun.status == "empty", not a
      fabricated "ok" result
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.drift.engine import (
    FeatureStatus,
    PSI_DRIFTED_THRESHOLD,
    PSI_MODERATE_THRESHOLD,
    JS_DRIFTED_THRESHOLD,
    KS_DRIFTED_THRESHOLD,
    MIN_USABLE_SAMPLES,
    evaluate_categorical_feature,
    evaluate_numeric_feature,
)
from app.models.drift_run import DriftRun, DriftRunStatus, TriggeredBy
from app.models.feature import Feature, FeatureDataType
from app.models.feature_drift_metric import FeatureDriftMetric
from app.models.feature_drift_result import FeatureDriftResult
from app.models.alert import Alert
from app.models.production_observation import ObservationStatus, ProductionObservation
from app.models.reference_raw_categorical import ReferenceRawCategorical
from app.models.reference_raw_sample import ReferenceRawSample
from app.models.reference_snapshot import ReferenceSnapshot
from app.services.registry_service import NotFoundError, get_owned_version

THRESHOLD_CONFIG_SNAPSHOT = {
    "psi_moderate": PSI_MODERATE_THRESHOLD,
    "psi_drifted": PSI_DRIFTED_THRESHOLD,
    "ks_drifted": KS_DRIFTED_THRESHOLD,
    "js_drifted": JS_DRIFTED_THRESHOLD,
    "min_usable_samples": MIN_USABLE_SAMPLES,
}


class NoReferenceSnapshotError(Exception):
    pass


def _resolve_reference_snapshot(db: Session, model_version_id: uuid.UUID, reference_snapshot_id: uuid.UUID | None):
    if reference_snapshot_id is not None:
        snapshot = (
            db.query(ReferenceSnapshot)
            .filter(
                ReferenceSnapshot.id == reference_snapshot_id,
                ReferenceSnapshot.model_version_id == model_version_id,
            )
            .first()
        )
        if snapshot is None:
            raise NotFoundError(reference_snapshot_id)
        return snapshot

    snapshot = (
        db.query(ReferenceSnapshot)
        .filter(ReferenceSnapshot.model_version_id == model_version_id)
        .order_by(ReferenceSnapshot.created_at.desc())
        .first()
    )
    if snapshot is None:
        raise NoReferenceSnapshotError(model_version_id)
    return snapshot


def _resolve_window_start(db: Session, model_version_id: uuid.UUID, version_created_at: datetime) -> datetime:
    previous_run = (
        db.query(DriftRun)
        .filter(DriftRun.model_version_id == model_version_id)
        .order_by(DriftRun.window_end.desc())
        .first()
    )
    return previous_run.window_end if previous_run is not None else version_created_at


def _reference_values_for_feature(db: Session, snapshot_id: uuid.UUID, feature: Feature) -> list:
    if feature.data_type == FeatureDataType.numeric:
        rows = (
            db.query(ReferenceRawSample)
            .filter(ReferenceRawSample.reference_snapshot_id == snapshot_id, ReferenceRawSample.feature_id == feature.id)
            .all()
        )
        return [r.value for r in rows]
    rows = (
        db.query(ReferenceRawCategorical)
        .filter(
            ReferenceRawCategorical.reference_snapshot_id == snapshot_id,
            ReferenceRawCategorical.feature_id == feature.id,
        )
        .all()
    )
    return [r.category_value for r in rows]


def run_drift_check(
    db: Session,
    user,
    model_version_id: uuid.UUID,
    reference_snapshot_id: uuid.UUID | None = None,
    window_end: datetime | None = None,
    triggered_by: TriggeredBy = TriggeredBy.manual,
) -> DriftRun:
    version = get_owned_version(db, user, model_version_id)  # raises NotFoundError if not owned
    snapshot = _resolve_reference_snapshot(db, version.id, reference_snapshot_id)

    window_end = window_end or datetime.now(timezone.utc)
    window_start = _resolve_window_start(db, version.id, version.created_at)

    features = db.query(Feature).filter(Feature.model_version_id == version.id).all()

    drift_run = DriftRun(
        model_version_id=version.id,
        reference_snapshot_id=snapshot.id,
        window_start=window_start,
        window_end=window_end,
        status=DriftRunStatus.empty,  # updated below once we know
        threshold_config_snapshot=THRESHOLD_CONFIG_SNAPSHOT,
        triggered_by=triggered_by,
    )
    db.add(drift_run)
    db.flush()

    total_rows = 0
    for feature in features:
        observations = (
            db.query(ProductionObservation)
            .filter(
                ProductionObservation.model_version_id == version.id,
                ProductionObservation.feature_id == feature.id,
                ProductionObservation.ingested_at > window_start,
                ProductionObservation.ingested_at <= window_end,
            )
            .all()
        )
        if not observations:
            continue
        total_rows += len(observations)

        n_valid = sum(1 for o in observations if o.status == ObservationStatus.valid)
        n_missing = sum(1 for o in observations if o.status == ObservationStatus.missing)
        n_invalid = sum(1 for o in observations if o.status == ObservationStatus.invalid)
        n_unseen = sum(1 for o in observations if o.status == ObservationStatus.unseen_category)

        reference_values = _reference_values_for_feature(db, snapshot.id, feature)

        if feature.data_type == FeatureDataType.numeric:
            production_values = [o.parsed_numeric for o in observations if o.status == ObservationStatus.valid]
            n_usable = n_valid
            if not reference_values:
                evaluation_status = FeatureStatus.insufficient_data
                metric_results = []
            else:
                evaluation = evaluate_numeric_feature(reference_values, production_values)
                evaluation_status = evaluation.feature_status
                metric_results = evaluation.metrics
        else:
            production_values = [
                o.parsed_category
                for o in observations
                if o.status in (ObservationStatus.valid, ObservationStatus.unseen_category)
            ]
            n_usable = n_valid + n_unseen
            if not reference_values:
                evaluation_status = FeatureStatus.insufficient_data
                metric_results = []
            else:
                evaluation = evaluate_categorical_feature(reference_values, production_values)
                evaluation_status = evaluation.feature_status
                metric_results = evaluation.metrics

        feature_result = FeatureDriftResult(
            drift_run_id=drift_run.id,
            feature_id=feature.id,
            rows_received=len(observations),
            n_valid=n_valid,
            n_missing=n_missing,
            n_invalid=n_invalid,
            n_unseen_category=n_unseen,
            n_usable=n_usable,
            feature_status=evaluation_status,
        )
        db.add(feature_result)
        db.flush()

        for metric in metric_results:
            db.add(
                FeatureDriftMetric(
                    feature_drift_result_id=feature_result.id,
                    metric_name=metric.metric_name,
                    metric_value=metric.metric_value,
                    p_value=metric.p_value,
                    threshold_used=metric.threshold_used,
                    status=metric.status,
                )
            )

        if evaluation_status == FeatureStatus.drifted:
            drifted_metric_names = ", ".join(m.metric_name for m in metric_results if m.status.value == "drifted")
            db.add(
                Alert(
                    model_version_id=version.id,
                    feature_id=feature.id,
                    drift_run_id=drift_run.id,
                    severity="high",
                    message=f"Feature '{feature.name}' drifted (metrics over threshold: {drifted_metric_names}).",
                )
            )

    drift_run.status = DriftRunStatus.completed if total_rows > 0 else DriftRunStatus.empty
    db.flush()
    return drift_run


def list_drift_runs(db: Session, user, model_version_id: uuid.UUID) -> list[DriftRun]:
    version = get_owned_version(db, user, model_version_id)
    return (
        db.query(DriftRun)
        .options(selectinload(DriftRun.feature_results))
        .filter(DriftRun.model_version_id == version.id)
        .order_by(DriftRun.created_at)
        .all()
    )


def get_owned_drift_run(db: Session, user, drift_run_id: uuid.UUID) -> DriftRun:
    from app.models.model import Model
    from app.models.model_version import ModelVersion

    run = (
        db.query(DriftRun)
        .join(ModelVersion, DriftRun.model_version_id == ModelVersion.id)
        .join(Model, ModelVersion.model_id == Model.id)
        .filter(DriftRun.id == drift_run_id, Model.user_id == user.id)
        .first()
    )
    if run is None:
        raise NotFoundError(drift_run_id)
    return run


def overall_drift_status(drift_run: DriftRun) -> str:
    """
    Deterministic aggregation documented here (spec section 8): DRIFTED if
    any feature drifted; else MODERATE if any feature is moderate; else OK
    if every feature was evaluated as ok; INSUFFICIENT_DATA only when there
    is no evaluated feature at all (e.g. an empty window).
    """
    statuses = [r.feature_status for r in drift_run.feature_results]
    if not statuses:
        return FeatureStatus.insufficient_data.value
    if any(s == FeatureStatus.drifted for s in statuses):
        return FeatureStatus.drifted.value
    if any(s == FeatureStatus.moderate for s in statuses):
        return FeatureStatus.moderate.value
    if all(s == FeatureStatus.insufficient_data for s in statuses):
        return FeatureStatus.insufficient_data.value
    return FeatureStatus.ok.value


