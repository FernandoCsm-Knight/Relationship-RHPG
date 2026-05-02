from typing import Optional
from uuid import uuid4
from sqlalchemy.orm import Session

from rhpg.models.schemas import WorkerCreate, GroupCreate, RelationshipCreate
from rhpg.storage.orm_models import WorkerORM, GroupORM, GroupMembershipORM, RelationshipORM


class WorkerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: WorkerCreate) -> WorkerORM:
        worker = WorkerORM(id=str(uuid4()), **data.model_dump())
        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def get_by_id(self, worker_id: str) -> Optional[WorkerORM]:
        return self.db.query(WorkerORM).filter(WorkerORM.id == worker_id).first()

    def get_all(self) -> list[WorkerORM]:
        return self.db.query(WorkerORM).all()

    def update(self, worker_id: str, fields: dict) -> Optional[WorkerORM]:
        worker = self.get_by_id(worker_id)
        if not worker:
            return None
        for key, value in fields.items():
            setattr(worker, key, value)
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def delete(self, worker_id: str) -> bool:
        worker = self.get_by_id(worker_id)
        if not worker:
            return False
        self.db.delete(worker)
        self.db.commit()
        return True


class GroupRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: GroupCreate) -> GroupORM:
        member_ids = data.member_ids
        group_data = data.model_dump(exclude={"member_ids"})
        group = GroupORM(id=str(uuid4()), **group_data)
        self.db.add(group)
        self.db.flush()

        for wid in member_ids:
            self.db.add(GroupMembershipORM(worker_id=wid, group_id=group.id))

        self.db.commit()
        self.db.refresh(group)
        return group

    def get_by_id(self, group_id: str) -> Optional[GroupORM]:
        return self.db.query(GroupORM).filter(GroupORM.id == group_id).first()

    def get_all(self) -> list[GroupORM]:
        return self.db.query(GroupORM).all()

    def get_member_ids(self, group_id: str) -> list[str]:
        rows = (
            self.db.query(GroupMembershipORM)
            .filter(GroupMembershipORM.group_id == group_id)
            .all()
        )
        return [r.worker_id for r in rows]

    def get_members(self, group_id: str) -> list[WorkerORM]:
        member_ids = self.get_member_ids(group_id)
        return self.db.query(WorkerORM).filter(WorkerORM.id.in_(member_ids)).all()

    def add_member(self, group_id: str, worker_id: str) -> None:
        existing = (
            self.db.query(GroupMembershipORM)
            .filter_by(group_id=group_id, worker_id=worker_id)
            .first()
        )
        if not existing:
            self.db.add(GroupMembershipORM(group_id=group_id, worker_id=worker_id))
            self.db.commit()

    def remove_member(self, group_id: str, worker_id: str) -> bool:
        row = (
            self.db.query(GroupMembershipORM)
            .filter_by(group_id=group_id, worker_id=worker_id)
            .first()
        )
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def update(self, group_id: str, fields: dict) -> Optional[GroupORM]:
        group = self.get_by_id(group_id)
        if not group:
            return None
        for key, value in fields.items():
            setattr(group, key, value)
        self.db.commit()
        self.db.refresh(group)
        return group

    def delete(self, group_id: str) -> bool:
        group = self.get_by_id(group_id)
        if not group:
            return False
        self.db.query(GroupMembershipORM).filter_by(group_id=group_id).delete()
        self.db.delete(group)
        self.db.commit()
        return True

    def get_all_memberships(self) -> dict[str, list[str]]:
        """Returns {group_id: [worker_ids]}."""
        rows = self.db.query(GroupMembershipORM).all()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row.group_id, []).append(row.worker_id)
        return result


class RelationshipRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: RelationshipCreate) -> RelationshipORM:
        weight = round(data.interaction_frequency * data.collaboration_quality, 4)
        rel = RelationshipORM(
            id=str(uuid4()),
            weight=weight,
            **data.model_dump(),
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def get_by_id(self, rel_id: str) -> Optional[RelationshipORM]:
        return self.db.query(RelationshipORM).filter(RelationshipORM.id == rel_id).first()

    def get_all(self) -> list[RelationshipORM]:
        return self.db.query(RelationshipORM).all()

    def get_for_worker(self, worker_id: str) -> list[RelationshipORM]:
        return (
            self.db.query(RelationshipORM)
            .filter(
                (RelationshipORM.source_id == worker_id)
                | (RelationshipORM.target_id == worker_id)
            )
            .all()
        )

    def delete(self, rel_id: str) -> bool:
        rel = self.get_by_id(rel_id)
        if not rel:
            return False
        self.db.delete(rel)
        self.db.commit()
        return True
