from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.models.schemas import (
    WorkerAnalysisResult,
    ClassifyRequest,
    LeaderboardEntry,
    WorkerAIEvaluationOut,
)
from rhpg.storage.repository import CandidateRepository, WorkerRepository, GroupRepository, RelationshipRepository
from rhpg.graph.builder import build_graphs
from rhpg.algorithms.classifier import run_full_analysis
from rhpg.algorithms.delta_score import compute_worker_delta, compute_group_quality_score
from rhpg.models.worker import Worker
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship, RelationshipType
from rhpg.services.fit_evaluator import FitEvaluatorError, OpenAIUnavailableError
from rhpg.services.worker_evaluator import evaluate_worker_context

router = APIRouter()


def _persist_results(results: list[WorkerAnalysisResult], db: Session) -> None:
    repo = WorkerRepository(db)
    for r in results:
        repo.update(
            r.worker_id,
            {
                "composite_score": r.composite_score,
                "pagerank_score": r.pagerank_score,
                "betweenness_centrality": r.betweenness_centrality,
                "performance_class": r.performance_class.value,
            },
        )


@router.post("/run", response_model=list[WorkerAnalysisResult])
def run_analysis(request: ClassifyRequest = ClassifyRequest(), db: Session = Depends(get_db)):
    """Execute the full analysis pipeline and persist results."""
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships, request)
    _persist_results(results, db)
    return results


@router.get("/results", response_model=list[WorkerAnalysisResult])
def get_results(db: Session = Depends(get_db)):
    """Return last persisted analysis results without re-running."""
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships)
    return results


@router.get("/results/{worker_id}", response_model=WorkerAnalysisResult)
def get_worker_result(worker_id: str, db: Session = Depends(get_db)):
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships)
    match = next((r for r in results if r.worker_id == worker_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Worker not found")
    return match


@router.post("/results/{worker_id}/evaluate-ai", response_model=WorkerAIEvaluationOut)
def evaluate_worker_ai(worker_id: str, db: Session = Depends(get_db)):
    worker_orm = WorkerRepository(db).get_by_id(worker_id)
    if not worker_orm:
        raise HTTPException(status_code=404, detail="Worker not found")

    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships)
    result_map = {r.worker_id: r for r in results}
    for worker in workers:
        result = result_map.get(worker.id)
        if result:
            worker.composite_score = result.composite_score
            worker.performance_class = result.performance_class
            worker.pagerank_score = result.pagerank_score
            worker.betweenness_centrality = result.betweenness_centrality

    target = next((w for w in workers if w.id == worker_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Worker not found")

    candidates = CandidateRepository(db).get_all(worker_id=worker_id)
    try:
        evaluation, _model = evaluate_worker_context(
            target,
            workers,
            groups,
            relationships,
            memberships,
            candidates,
        )
    except OpenAIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FitEvaluatorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return evaluation


@router.get("/delta/{worker_id}/{group_id}")
def get_delta(worker_id: str, group_id: str, db: Session = Depends(get_db)):
    worker_orm = WorkerRepository(db).get_by_id(worker_id)
    if not worker_orm:
        raise HTTPException(status_code=404, detail="Worker not found")
    group_orm = GroupRepository(db).get_by_id(group_id)
    if not group_orm:
        raise HTTPException(status_code=404, detail="Group not found")

    member_orms = GroupRepository(db).get_members(group_id)
    rel_orms = RelationshipRepository(db).get_all()

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
        member_ids=[m.id for m in member_orms],
    )
    target = next((w for w in workers if w.id == worker_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Worker is not a member of this group")

    delta = compute_worker_delta(target, group, workers, relationships)
    return {"worker_id": worker_id, "group_id": group_id, "delta": delta}


@router.post("/classify", response_model=list[WorkerAnalysisResult])
def classify(request: ClassifyRequest, db: Session = Depends(get_db)):
    """Re-classify workers with custom weights/method without persisting."""
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    return run_full_analysis(workers, groups, relationships, memberships, request)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(top: int = 10, db: Session = Depends(get_db)):
    """Top-N workers ranked by composite score."""
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships)
    sorted_results = sorted(results, key=lambda r: r.composite_score, reverse=True)
    return [
        LeaderboardEntry(
            rank=i + 1,
            worker_id=r.worker_id,
            name=r.name,
            role=r.role,
            department=r.department,
            composite_score=r.composite_score,
            performance_class=r.performance_class,
        )
        for i, r in enumerate(sorted_results[:top])
    ]
