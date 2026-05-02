from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.models.schemas import CandidateCreate, CandidateUpdate, CandidateOut
from rhpg.services.fit_evaluator import (
    FitEvaluatorError,
    OpenAIUnavailableError,
    evaluate_candidate_fit,
)
from rhpg.storage.repository import (
    CandidateRepository,
    GroupRepository,
    WorkerRepository,
    load_json_list,
)

router = APIRouter()


def _candidate_to_out(candidate, db: Session) -> CandidateOut:
    worker = WorkerRepository(db).get_by_id(candidate.worker_id)
    group = GroupRepository(db).get_by_id(candidate.group_id)
    return CandidateOut(
        id=candidate.id,
        worker_id=candidate.worker_id,
        worker_name=worker.name if worker else "Colaborador removido",
        group_id=candidate.group_id,
        group_name=group.name if group else "Equipe removida",
        status=candidate.status,
        target_role=candidate.target_role,
        notes=candidate.notes,
        fit_score=candidate.fit_score,
        recommendation=candidate.recommendation,
        confidence=candidate.confidence,
        summary=candidate.summary,
        strengths=load_json_list(candidate.strengths_json),
        risks=load_json_list(candidate.risks_json),
        skill_matches=load_json_list(candidate.skill_matches_json),
        skill_gaps=load_json_list(candidate.skill_gaps_json),
        interview_questions=load_json_list(candidate.interview_questions_json),
        model=candidate.model,
        evaluated_at=candidate.evaluated_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


@router.post("/", response_model=CandidateOut, status_code=201)
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    if not WorkerRepository(db).get_by_id(data.worker_id):
        raise HTTPException(status_code=404, detail="Worker not found")
    if not GroupRepository(db).get_by_id(data.group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    candidate = CandidateRepository(db).create(data)
    return _candidate_to_out(candidate, db)


@router.get("/", response_model=list[CandidateOut])
def list_candidates(
    worker_id: Optional[str] = None,
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    candidates = CandidateRepository(db).get_all(worker_id, group_id, status)
    return [_candidate_to_out(candidate, db) for candidate in candidates]


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = CandidateRepository(db).get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_to_out(candidate, db)


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(candidate_id: str, data: CandidateUpdate, db: Session = Depends(get_db)):
    candidate = CandidateRepository(db).update(candidate_id, data)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_to_out(candidate, db)


@router.post("/{candidate_id}/evaluate", response_model=CandidateOut)
def evaluate_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate_repo = CandidateRepository(db)
    candidate = candidate_repo.get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    worker = WorkerRepository(db).get_by_id(candidate.worker_id)
    group = GroupRepository(db).get_by_id(candidate.group_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    try:
        evaluation, model = evaluate_candidate_fit(worker, group, candidate)
    except OpenAIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FitEvaluatorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    saved = candidate_repo.save_ai_evaluation(candidate_id, evaluation, model)
    if not saved:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_to_out(saved, db)
