"""
Model registry business logic. Every read/write here is scoped to the
owning user — there is no path in this module that can return or mutate
another user's resource.
"""
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.feature import Feature, FeatureDataType
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.user import User


class DuplicateNameError(Exception):
    pass


class NotFoundError(Exception):
    pass


# ---- Models ----

def create_model(db: Session, user: User, name: str) -> Model:
    model = Model(user_id=user.id, name=name)
    db.add(model)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateNameError(name) from exc
    return model


def list_models(db: Session, user: User) -> list[Model]:
    return db.query(Model).filter(Model.user_id == user.id).order_by(Model.created_at).all()


def get_owned_model(db: Session, user: User, model_id: uuid.UUID) -> Model:
    model = db.query(Model).filter(Model.id == model_id, Model.user_id == user.id).first()
    if model is None:
        raise NotFoundError(model_id)
    return model


# ---- Model versions ----

def create_version(db: Session, user: User, model_id: uuid.UUID, version_label: str) -> ModelVersion:
    model = get_owned_model(db, user, model_id)  # raises NotFoundError if not owned
    version = ModelVersion(model_id=model.id, version_label=version_label)
    db.add(version)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateNameError(version_label) from exc
    return version


def list_versions(db: Session, user: User, model_id: uuid.UUID) -> list[ModelVersion]:
    get_owned_model(db, user, model_id)  # ownership check
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.model_id == model_id)
        .order_by(ModelVersion.created_at)
        .all()
    )


def get_owned_version(db: Session, user: User, version_id: uuid.UUID) -> ModelVersion:
    version = (
        db.query(ModelVersion)
        .join(Model, ModelVersion.model_id == Model.id)
        .filter(ModelVersion.id == version_id, Model.user_id == user.id)
        .first()
    )
    if version is None:
        raise NotFoundError(version_id)
    return version


# ---- Features ----

def create_feature(
    db: Session, user: User, version_id: uuid.UUID, name: str, data_type: FeatureDataType
) -> Feature:
    version = get_owned_version(db, user, version_id)  # ownership check
    feature = Feature(model_version_id=version.id, name=name, data_type=data_type)
    db.add(feature)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateNameError(name) from exc
    return feature


def list_features(db: Session, user: User, version_id: uuid.UUID) -> list[Feature]:
    get_owned_version(db, user, version_id)  # ownership check
    return (
        db.query(Feature)
        .filter(Feature.model_version_id == version_id)
        .order_by(Feature.created_at)
        .all()
    )
