from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.models.schemas import WorkerCreate, WorkerOut
from rhpg.storage.repository import WorkerRepository

router = APIRouter()


@router.post("/", response_model=WorkerOut, status_code=201)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    return WorkerRepository(db).create(data)


@router.get("/", response_model=list[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return WorkerRepository(db).get_all()


@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: str, db: Session = Depends(get_db)):
    worker = WorkerRepository(db).get_by_id(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.put("/{worker_id}", response_model=WorkerOut)
def update_worker(worker_id: str, data: WorkerCreate, db: Session = Depends(get_db)):
    updated = WorkerRepository(db).update(worker_id, data.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Worker not found")
    return updated


@router.delete("/{worker_id}", status_code=204)
def delete_worker(worker_id: str, db: Session = Depends(get_db)):
    if not WorkerRepository(db).delete(worker_id):
        raise HTTPException(status_code=404, detail="Worker not found")
