from sqlalchemy.orm import Session

from rhpg.models.worker import Worker
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship, RelationshipType
from rhpg.storage.repository import WorkerRepository, GroupRepository, RelationshipRepository, load_json_list
from rhpg.graph.nx_graph import WorkerGraph
from rhpg.graph.hypergraph import WorkerHypergraph


def _orm_to_worker(orm) -> Worker:
    return Worker(
        id=orm.id,
        name=orm.name,
        role=orm.role,
        department=orm.department,
        proficiency_score=orm.proficiency_score,
        individual_performance_score=orm.individual_performance_score,
        tenure_years=orm.tenure_years,
        email=orm.email,
        location=orm.location,
        seniority_level=orm.seniority_level,
        resume_text=orm.resume_text,
        skills=load_json_list(orm.skills_json),
        education=load_json_list(orm.education_json),
        certifications=load_json_list(orm.certifications_json),
        languages=load_json_list(orm.languages_json),
        past_projects=load_json_list(orm.past_projects_json),
        achievements_text=orm.achievements_text,
        availability_notes=orm.availability_notes,
        linkedin_url=orm.linkedin_url,
        portfolio_url=orm.portfolio_url,
        pagerank_score=orm.pagerank_score,
        betweenness_centrality=orm.betweenness_centrality,
        composite_score=orm.composite_score,
        performance_class=orm.performance_class,
    )


def _orm_to_group(orm, member_ids: list[str]) -> Group:
    return Group(
        id=orm.id,
        name=orm.name,
        project_name=orm.project_name,
        department=orm.department,
        baseline_work_quality=orm.baseline_work_quality,
        project_outcome_score=orm.project_outcome_score,
        open_role_title=orm.open_role_title,
        required_seniority=orm.required_seniority,
        team_context=orm.team_context,
        required_skills=load_json_list(orm.required_skills_json),
        preferred_skills=load_json_list(orm.preferred_skills_json),
        responsibilities=load_json_list(orm.responsibilities_json),
        hiring_notes=orm.hiring_notes,
        member_ids=member_ids,
        adjusted_work_quality=orm.adjusted_work_quality,
    )


def _orm_to_relationship(orm) -> Relationship:
    return Relationship(
        id=orm.id,
        source_id=orm.source_id,
        target_id=orm.target_id,
        rel_type=RelationshipType(orm.rel_type),
        interaction_frequency=orm.interaction_frequency,
        collaboration_quality=orm.collaboration_quality,
        weight=orm.weight,
    )


def load_domain_objects(
    db: Session,
) -> tuple[list[Worker], list[Group], list[Relationship]]:
    worker_repo = WorkerRepository(db)
    group_repo = GroupRepository(db)
    rel_repo = RelationshipRepository(db)

    workers = [_orm_to_worker(w) for w in worker_repo.get_all()]
    memberships = group_repo.get_all_memberships()
    groups = [
        _orm_to_group(g, memberships.get(g.id, []))
        for g in group_repo.get_all()
    ]
    relationships = [_orm_to_relationship(r) for r in rel_repo.get_all()]

    return workers, groups, relationships


def build_graphs(
    db: Session,
) -> tuple[WorkerGraph, WorkerHypergraph, list[Worker], list[Group], list[Relationship]]:
    workers, groups, relationships = load_domain_objects(db)

    nx_graph = WorkerGraph()
    nx_graph.build(workers, groups, relationships)

    hypergraph = WorkerHypergraph()
    hypergraph.build(groups)

    return nx_graph, hypergraph, workers, groups, relationships
