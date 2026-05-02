from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.models.schemas import RelationshipCreate, RelationshipOut
from rhpg.storage.repository import RelationshipRepository

router = APIRouter()


@router.post("/", response_model=RelationshipOut, status_code=201)
def create_relationship(data: RelationshipCreate, db: Session = Depends(get_db)):
    return RelationshipRepository(db).create(data)


@router.get("/", response_model=list[RelationshipOut])
def list_relationships(db: Session = Depends(get_db)):
    return RelationshipRepository(db).get_all()


@router.get("/{rel_id}", response_model=RelationshipOut)
def get_relationship(rel_id: str, db: Session = Depends(get_db)):
    rel = RelationshipRepository(db).get_by_id(rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return rel


@router.delete("/{rel_id}", status_code=204)
def delete_relationship(rel_id: str, db: Session = Depends(get_db)):
    if not RelationshipRepository(db).delete(rel_id):
        raise HTTPException(status_code=404, detail="Relationship not found")
