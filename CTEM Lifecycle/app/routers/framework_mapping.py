from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.framework_mapping import (
    FrameworkMappingRequest,
    FrameworkMappingResponse
)
from app.services.framework_mapping_service import (
    create_framework_mapping,
    get_framework_mappings
)

router = APIRouter(
    prefix="/ctem",
    tags=["Framework Mapping"]
)


@router.post(
    "/frameworks/map",
    response_model=FrameworkMappingResponse
)
def map_framework(
    request: FrameworkMappingRequest,
    db: Session = Depends(get_db)
):
    return create_framework_mapping(
        db=db,
        mapping=request
    )


@router.get(
    "/cycles/{cycle_id}/framework-mappings",
    response_model=list[FrameworkMappingResponse]
)
def list_framework_mappings(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    return get_framework_mappings(db, cycle_id)
