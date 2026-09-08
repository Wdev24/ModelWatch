"""
Production observation ingestion.

Policy (V1, per spec section 7):
- Every observation is stored — valid, missing, invalid, or unseen_category
  — never silently discarded.
- Unknown feature references are rejected for the whole request (422) rather
  than partially ingested, since there's no feature_id to attach the row to
  and a partial batch would be a worse silent failure.
- Unseen-category detection uses the most recent reference snapshot's
  category set for that feature. If the feature has no reference baseline
  yet, categorical values cannot be judged "unseen" and are recorded as
  valid — this is a documented V1 limitation, not a mistake.
"""
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.feature import Feature, FeatureDataType
from app.models.production_observation import ObservationStatus, ProductionObservation
from app.models.reference_raw_categorical import ReferenceRawCategorical
from app.models.reference_snapshot import ReferenceSnapshot
from app.services.registry_service import NotFoundError, get_owned_version


class UnknownFeatureError(Exception):
    """Raised when an observation references a feature_id not on this model version."""
    def __init__(self, feature_ids: set[uuid.UUID]):
        self.feature_ids = feature_ids
        super().__init__(f"Unknown feature ids: {feature_ids}")


def _is_empty(raw_value: str | None) -> bool:
    return raw_value is None or raw_value.strip() == ""


def _known_categories_by_feature(db: Session, model_version_id: uuid.UUID) -> dict[uuid.UUID, set[str]]:
    latest_snapshot = (
        db.query(ReferenceSnapshot)
        .filter(ReferenceSnapshot.model_version_id == model_version_id)
        .order_by(ReferenceSnapshot.created_at.desc())
        .first()
    )
    if latest_snapshot is None:
        return {}

    rows = (
        db.query(ReferenceRawCategorical)
        .filter(ReferenceRawCategorical.reference_snapshot_id == latest_snapshot.id)
        .all()
    )
    known: dict[uuid.UUID, set[str]] = {}
    for row in rows:
        known.setdefault(row.feature_id, set()).add(row.category_value)
    return known


def _classify_and_build(
    feature: Feature,
    raw_value: str | None,
    observed_at: datetime | None,
    known_categories: set[str] | None,
) -> ProductionObservation:
    if _is_empty(raw_value):
        return ProductionObservation(
            model_version_id=feature.model_version_id,
            feature_id=feature.id,
            observed_at=observed_at,
            raw_value=raw_value,
            status=ObservationStatus.missing,
        )

    stripped = raw_value.strip()

    if feature.data_type == FeatureDataType.numeric:
        try:
            numeric = float(stripped)
        except ValueError:
            return ProductionObservation(
                model_version_id=feature.model_version_id,
                feature_id=feature.id,
                observed_at=observed_at,
                raw_value=raw_value,
                status=ObservationStatus.invalid,
            )
        return ProductionObservation(
            model_version_id=feature.model_version_id,
            feature_id=feature.id,
            observed_at=observed_at,
            raw_value=raw_value,
            parsed_numeric=numeric,
            status=ObservationStatus.valid,
        )

    # categorical
    if known_categories is not None and stripped not in known_categories:
        status = ObservationStatus.unseen_category
    else:
        status = ObservationStatus.valid
    return ProductionObservation(
        model_version_id=feature.model_version_id,
        feature_id=feature.id,
        observed_at=observed_at,
        raw_value=raw_value,
        parsed_category=stripped,
        status=status,
    )


def ingest_observations(db: Session, user, model_version_id: uuid.UUID, observations: list) -> list[ProductionObservation]:
    """
    observations: list of objects with .feature_id, .raw_value (str | None),
    .observed_at (datetime | None).
    """
    version = get_owned_version(db, user, model_version_id)  # raises NotFoundError if not owned/found

    features = db.query(Feature).filter(Feature.model_version_id == version.id).all()
    features_by_id = {f.id: f for f in features}

    requested_ids = {o.feature_id for o in observations}
    unknown = requested_ids - set(features_by_id)
    if unknown:
        raise UnknownFeatureError(unknown)

    known_categories_by_feature = _known_categories_by_feature(db, version.id)

    rows: list[ProductionObservation] = []
    for obs in observations:
        feature = features_by_id[obs.feature_id]
        known = known_categories_by_feature.get(feature.id)
        row = _classify_and_build(feature, obs.raw_value, obs.observed_at, known)
        rows.append(row)

    db.add_all(rows)
    db.flush()
    return rows
