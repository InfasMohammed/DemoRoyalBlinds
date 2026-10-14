from fastapi import APIRouter, HTTPException

from ..business_data import load_operations
from ..record_creation import MaterialCreate, RecordConflict, create_material

router = APIRouter(tags=["business"])


@router.get("/catalog")
def catalog():
    return load_operations()


@router.post("/materials", status_code=201)
def add_material(request: MaterialCreate):
    try:
        return create_material(request)
    except RecordConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
