from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.models.schemas import GroupCreate, GroupOut, GroupQualityOut
from rhpg.storage.repository import GroupRepository, WorkerRepository, RelationshipRepository
from rhpg.models.group import Group
from rhpg.models.relationship import RelationshipType, Relationship
from rhpg.algorithms.delta_score import compute_group_quality_score

router = APIRouter()


def _orm_group_to_out(orm, member_ids: list[str]) -> GroupOut:
    return GroupOut(
        id=orm.id,
        name=orm.name,
        project_name=orm.project_name,
        department=orm.department,
        baseline_work_quality=orm.baseline_work_quality,
        project_outcome_score=orm.project_outcome_score,
        adjusted_work_quality=orm.adjusted_work_quality,
        member_ids=member_ids,
    )


@router.post("/", response_model=GroupOut, status_code=201)
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    repo = GroupRepository(db)
    orm = repo.create(data)
    member_ids = repo.get_member_ids(orm.id)
    return _orm_group_to_out(orm, member_ids)


@router.get("/", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db)):
    repo = GroupRepository(db)
    groups = repo.get_all()
    return [_orm_group_to_out(g, repo.get_member_ids(g.id)) for g in groups]


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: str, db: Session = Depends(get_db)):
    repo = GroupRepository(db)
    group = repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return _orm_group_to_out(group, repo.get_member_ids(group_id))


@router.post("/{group_id}/members/{worker_id}", status_code=204)
def add_member(group_id: str, worker_id: str, db: Session = Depends(get_db)):
    group_repo = GroupRepository(db)
    if not group_repo.get_by_id(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    if not WorkerRepository(db).get_by_id(worker_id):
        raise HTTPException(status_code=404, detail="Worker not found")
    group_repo.add_member(group_id, worker_id)


@router.delete("/{group_id}/members/{worker_id}", status_code=204)
def remove_member(group_id: str, worker_id: str, db: Session = Depends(get_db)):
    if not GroupRepository(db).remove_member(group_id, worker_id):
        raise HTTPException(status_code=404, detail="Membership not found")


@router.get("/{group_id}/quality", response_model=GroupQualityOut)
def get_group_quality(group_id: str, db: Session = Depends(get_db)):
    group_repo = GroupRepository(db)
    group_orm = group_repo.get_by_id(group_id)
    if not group_orm:
        raise HTTPException(status_code=404, detail="Group not found")

    member_ids = group_repo.get_member_ids(group_id)
    member_orms = group_repo.get_members(group_id)
    rel_orms = RelationshipRepository(db).get_all()

    from rhpg.models.worker import Worker
    workers = [
        Worker(
            id=m.id, name=m.name, role=m.role, department=m.department,
            proficiency_score=m.proficiency_score,
            individual_performance_score=m.individual_performance_score,
            tenure_years=m.tenure_years,
        )
        for m in member_orms
    ]
    relationships = [
        Relationship(
            id=r.id, source_id=r.source_id, target_id=r.target_id,
            rel_type=RelationshipType(r.rel_type),
            interaction_frequency=r.interaction_frequency,
            collaboration_quality=r.collaboration_quality,
        )
        for r in rel_orms
    ]

    group = Group(
        id=group_orm.id, name=group_orm.name, project_name=group_orm.project_name,
        department=group_orm.department,
        baseline_work_quality=group_orm.baseline_work_quality,
        project_outcome_score=group_orm.project_outcome_score,
        member_ids=member_ids,
    )
    quality = compute_group_quality_score(group, workers, relationships)

    return GroupQualityOut(
        group_id=group_id,
        baseline_work_quality=group_orm.baseline_work_quality,
        adjusted_work_quality=quality,
    )
