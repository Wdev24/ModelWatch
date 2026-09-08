import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.registry import (
    FeatureCreate,
    FeatureOut,
    ModelCreate,
    ModelOut,
    ModelVersionCreate,
    ModelVersionOut,
)
from app.services.registry_service import (
    DuplicateNameError,
    NotFoundError,
    create_feature,
    create_model,
    create_version,
    list_features,
    list_models,
    list_versions,
)

router = APIRouter(tags=["registry"])


@router.post("/models", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
def create_model_endpoint(
    payload: ModelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelOut:
    try:
        model = create_model(db, current_user, payload.name)
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Model name already exists.")
    db.commit()
    db.refresh(model)
    return ModelOut.model_validate(model)


@router.get("/models", response_model=list[ModelOut])
def list_models_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ModelOut]:
    return [ModelOut.model_validate(m) for m in list_models(db, current_user)]


@router.post(
    "/models/{model_id}/versions", response_model=ModelVersionOut, status_code=status.HTTP_201_CREATED
)
def create_version_endpoint(
    model_id: uuid.UUID,
    payload: ModelVersionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelVersionOut:
    try:
        version = create_version(db, current_user, model_id, payload.version_label)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found.")
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version label already exists.")
    db.commit()
    db.refresh(version)
    return ModelVersionOut.model_validate(version)


@router.get("/models/{model_id}/versions", response_model=list[ModelVersionOut])
def list_versions_endpoint(
    model_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ModelVersionOut]:
    try:
        versions = list_versions(db, current_user, model_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found.")
    return [ModelVersionOut.model_validate(v) for v in versions]


@router.post(
    "/versions/{version_id}/features", response_model=FeatureOut, status_code=status.HTTP_201_CREATED
)
def create_feature_endpoint(
    version_id: uuid.UUID,
    payload: FeatureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeatureOut:
    try:
        feature = create_feature(db, current_user, version_id, payload.name, payload.data_type)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Feature name already exists.")
    db.commit()
    db.refresh(feature)
    return FeatureOut.model_validate(feature)


@router.get("/versions/{version_id}/features", response_model=list[FeatureOut])
def list_features_endpoint(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FeatureOut]:
    try:
        features = list_features(db, current_user, version_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return [FeatureOut.model_validate(f) for f in features]
