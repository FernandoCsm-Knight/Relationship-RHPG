from rhpg.storage.seed import seed
from rhpg.storage.database import SessionLocal
from rhpg.storage.orm_models import WorkerORM, GroupORM, CandidateEvaluationORM


def test_seed_populates_enriched_profiles_and_candidates():
    seed()
    db = SessionLocal()
    try:
        worker = db.query(WorkerORM).first()
        group = db.query(GroupORM).first()
        candidates = db.query(CandidateEvaluationORM).all()

        assert worker is not None
        assert worker.resume_text
        assert worker.skills_json != "[]"
        assert worker.past_projects_json != "[]"

        assert group is not None
        assert group.open_role_title
        assert group.required_skills_json != "[]"
        assert group.responsibilities_json != "[]"

        assert len(candidates) >= 10
        assert all(c.worker_id and c.group_id for c in candidates)
    finally:
        db.close()
