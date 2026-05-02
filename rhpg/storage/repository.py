import json
from typing import Optional
from uuid import uuid4
from datetime import UTC, datetime
from sqlalchemy.orm import Session

from rhpg.models.schemas import WorkerCreate, GroupCreate, RelationshipCreate, CandidateCreate, CandidateUpdate, CandidateAIEvaluationOut
from rhpg.storage.orm_models import WorkerORM, GroupORM, GroupMembershipORM, RelationshipORM, CandidateEvaluationORM


_WORKER_JSON_FIELDS = {
    "skills": "skills_json",
    "education": "education_json",
    "certifications": "certifications_json",
    "languages": "languages_json",
    "past_projects": "past_projects_json",
}

_GROUP_JSON_FIELDS = {
    "required_skills": "required_skills_json",
    "preferred_skills": "preferred_skills_json",
    "responsibilities": "responsibilities_json",
}

_CANDIDATE_JSON_FIELDS = {
    "strengths": "strengths_json",
    "risks": "risks_json",
    "skill_matches": "skill_matches_json",
    "skill_gaps": "skill_gaps_json",
    "interview_questions": "interview_questions_json",
}


def dump_json_list(value: list[str] | None) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _encode_json_fields(data: dict, mapping: dict[str, str]) -> dict:
    encoded = dict(data)
    for public_name, column_name in mapping.items():
        if public_name in encoded:
            encoded[column_name] = dump_json_list(encoded.pop(public_name))
    return encoded


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WorkerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: WorkerCreate) -> WorkerORM:
        worker = WorkerORM(id=str(uuid4()), **_encode_json_fields(data.model_dump(), _WORKER_JSON_FIELDS))
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
        fields = _encode_json_fields(fields, _WORKER_JSON_FIELDS)
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

    def get_candidates(self, worker_id: str) -> list[CandidateEvaluationORM]:
        return (
            self.db.query(CandidateEvaluationORM)
            .filter(CandidateEvaluationORM.worker_id == worker_id)
            .all()
        )


class GroupRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: GroupCreate) -> GroupORM:
        member_ids = data.member_ids
        group_data = _encode_json_fields(data.model_dump(exclude={"member_ids"}), _GROUP_JSON_FIELDS)
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
        fields = _encode_json_fields(fields, _GROUP_JSON_FIELDS)
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


class CandidateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: CandidateCreate) -> CandidateEvaluationORM:
        candidate = CandidateEvaluationORM(id=str(uuid4()), **data.model_dump())
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def get_by_id(self, candidate_id: str) -> Optional[CandidateEvaluationORM]:
        return (
            self.db.query(CandidateEvaluationORM)
            .filter(CandidateEvaluationORM.id == candidate_id)
            .first()
        )

    def get_all(
        self,
        worker_id: Optional[str] = None,
        group_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[CandidateEvaluationORM]:
        query = self.db.query(CandidateEvaluationORM)
        if worker_id:
            query = query.filter(CandidateEvaluationORM.worker_id == worker_id)
        if group_id:
            query = query.filter(CandidateEvaluationORM.group_id == group_id)
        if status:
            query = query.filter(CandidateEvaluationORM.status == status)
        return query.order_by(CandidateEvaluationORM.created_at.desc()).all()

    def update(self, candidate_id: str, data: CandidateUpdate) -> Optional[CandidateEvaluationORM]:
        candidate = self.get_by_id(candidate_id)
        if not candidate:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(candidate, key, value)
        candidate.updated_at = _now_utc()
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def save_ai_evaluation(
        self,
        candidate_id: str,
        evaluation: CandidateAIEvaluationOut,
        model: str,
    ) -> Optional[CandidateEvaluationORM]:
        candidate = self.get_by_id(candidate_id)
        if not candidate:
            return None
        candidate.fit_score = evaluation.fit_score
        candidate.recommendation = evaluation.recommendation
        candidate.confidence = evaluation.confidence
        candidate.summary = evaluation.summary
        for public_name, column_name in _CANDIDATE_JSON_FIELDS.items():
            setattr(candidate, column_name, dump_json_list(getattr(evaluation, public_name)))
        candidate.model = model
        candidate.evaluated_at = _now_utc()
        candidate.updated_at = _now_utc()
        self.db.commit()
        self.db.refresh(candidate)
        return candidate
