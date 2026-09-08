"""
Reference snapshot business logic.

Design decision (V1, per spec section 6): a snapshot is created for a
model version as a whole. The caller supplies raw values only for the
features they're updating; every other feature that already has a prior
baseline is copied forward unchanged into the new snapshot, so
`DriftRun.reference_snapshot_id` always points to one complete, immutable
baseline no matter which features were actually re-uploaded.
"""
import statistics as pystats
import uuid

from sqlalchemy.orm import Session

from app.models.feature import Feature, FeatureDataType
from app.models.reference_raw_categorical import ReferenceRawCategorical
from app.models.reference_raw_sample import ReferenceRawSample
from app.models.reference_snapshot import ReferenceSnapshot
from app.models.reference_stats import ReferenceStats
from app.services.registry_service import NotFoundError, get_owned_version


class NoDataForFeatureError(Exception):
    """Raised when a numeric/categorical upload payload is empty."""
    pass


class MismatchedDataTypeError(Exception):
    """Raised when the uploaded value list doesn't match the feature's declared data_type."""
    pass


def _compute_numeric_stats(values: list[float | None]) -> tuple[dict, int, int]:
    valid = [v for v in values if v is not None]
    n_missing = len(values) - len(valid)
    if valid:
        stats = {
            "count": len(valid),
            "mean": pystats.fmean(valid),
            "std": pystats.pstdev(valid) if len(valid) > 1 else 0.0,
            "min": min(valid),
            "max": max(valid),
        }
    else:
        stats = {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    return stats, len(valid), n_missing


def _compute_categorical_stats(values: list[str | None]) -> tuple[dict, int, int]:
    valid = [v for v in values if v is not None]
    n_missing = len(values) - len(valid)
    counts: dict[str, int] = {}
    for v in valid:
        counts[v] = counts.get(v, 0) + 1
    stats = {"count": len(valid), "category_counts": counts}
    return stats, len(valid), n_missing


def create_reference_snapshot(
    db: Session,
    user,
    model_version_id: uuid.UUID,
    label: str,
    feature_uploads: list,  # list of FeatureUpload-like objects: feature_id, numeric_values, categorical_values
    source_metadata: dict | None = None,
) -> ReferenceSnapshot:
    version = get_owned_version(db, user, model_version_id)  # raises NotFoundError if not owned

    features = db.query(Feature).filter(Feature.model_version_id == version.id).all()
    features_by_id = {f.id: f for f in features}

    numeric_uploads: dict[uuid.UUID, list] = {}
    categorical_uploads: dict[uuid.UUID, list] = {}

    for upload in feature_uploads:
        feature = features_by_id.get(upload.feature_id)
        if feature is None:
            raise NotFoundError(upload.feature_id)

        if feature.data_type == FeatureDataType.numeric:
            if upload.numeric_values is None or upload.categorical_values is not None:
                raise MismatchedDataTypeError(feature.id)
            numeric_uploads[feature.id] = upload.numeric_values
        else:
            if upload.categorical_values is None or upload.numeric_values is not None:
                raise MismatchedDataTypeError(feature.id)
            categorical_uploads[feature.id] = upload.categorical_values

    # Find the most recent prior snapshot (if any) to copy forward from.
    previous_snapshot = (
        db.query(ReferenceSnapshot)
        .filter(ReferenceSnapshot.model_version_id == version.id)
        .order_by(ReferenceSnapshot.created_at.desc())
        .first()
    )

    snapshot = ReferenceSnapshot(
        model_version_id=version.id, label=label, source_metadata=source_metadata
    )
    db.add(snapshot)
    db.flush()

    for feature in features:
        if feature.id in numeric_uploads or feature.id in categorical_uploads:
            _write_new_feature_data(db, snapshot, feature, numeric_uploads, categorical_uploads)
        elif previous_snapshot is not None:
            _copy_forward_feature_data(db, previous_snapshot, snapshot, feature)
        # else: feature has no baseline yet and none was uploaded now — nothing to write.

    db.flush()
    return snapshot


def _write_new_feature_data(db, snapshot, feature, numeric_uploads, categorical_uploads) -> None:
    if feature.data_type == FeatureDataType.numeric:
        values = numeric_uploads[feature.id]
        if not values:
            raise NoDataForFeatureError(feature.id)
        stats, n_valid, n_missing = _compute_numeric_stats(values)
        db.add_all(
            ReferenceRawSample(reference_snapshot_id=snapshot.id, feature_id=feature.id, value=v)
            for v in values
            if v is not None
        )
    else:
        values = categorical_uploads[feature.id]
        if not values:
            raise NoDataForFeatureError(feature.id)
        stats, n_valid, n_missing = _compute_categorical_stats(values)
        db.add_all(
            ReferenceRawCategorical(
                reference_snapshot_id=snapshot.id, feature_id=feature.id, category_value=v
            )
            for v in values
            if v is not None
        )

    db.add(
        ReferenceStats(
            reference_snapshot_id=snapshot.id,
            feature_id=feature.id,
            statistics=stats,
            n_valid=n_valid,
            n_missing=n_missing,
        )
    )


def _copy_forward_feature_data(db, previous_snapshot, new_snapshot, feature) -> None:
    prev_stats = (
        db.query(ReferenceStats)
        .filter(
            ReferenceStats.reference_snapshot_id == previous_snapshot.id,
            ReferenceStats.feature_id == feature.id,
        )
        .first()
    )
    if prev_stats is None:
        return  # feature had no baseline in the previous snapshot either

    db.add(
        ReferenceStats(
            reference_snapshot_id=new_snapshot.id,
            feature_id=feature.id,
            statistics=prev_stats.statistics,
            n_valid=prev_stats.n_valid,
            n_missing=prev_stats.n_missing,
        )
    )

    if feature.data_type == FeatureDataType.numeric:
        prev_rows = (
            db.query(ReferenceRawSample)
            .filter(
                ReferenceRawSample.reference_snapshot_id == previous_snapshot.id,
                ReferenceRawSample.feature_id == feature.id,
            )
            .all()
        )
        db.add_all(
            ReferenceRawSample(reference_snapshot_id=new_snapshot.id, feature_id=feature.id, value=row.value)
            for row in prev_rows
        )
    else:
        prev_rows = (
            db.query(ReferenceRawCategorical)
            .filter(
                ReferenceRawCategorical.reference_snapshot_id == previous_snapshot.id,
                ReferenceRawCategorical.feature_id == feature.id,
            )
            .all()
        )
        db.add_all(
            ReferenceRawCategorical(
                reference_snapshot_id=new_snapshot.id,
                feature_id=feature.id,
                category_value=row.category_value,
            )
            for row in prev_rows
        )


def list_snapshots(db: Session, user, model_version_id: uuid.UUID) -> list[ReferenceSnapshot]:
    version = get_owned_version(db, user, model_version_id)
    return (
        db.query(ReferenceSnapshot)
        .filter(ReferenceSnapshot.model_version_id == version.id)
        .order_by(ReferenceSnapshot.created_at)
        .all()
    )
