import json
import os
from statistics import mean

from rhpg.models.schemas import WorkerAIEvaluationOut
from rhpg.services.fit_evaluator import (
    DEFAULT_OPENAI_MODEL,
    FitEvaluatorError,
    OpenAIUnavailableError,
    _strict_json_schema,
)
from rhpg.storage.repository import load_json_list


def _list_attr(obj, list_name: str, json_name: str) -> list[str]:
    if hasattr(obj, list_name):
        return getattr(obj, list_name) or []
    return load_json_list(getattr(obj, json_name, None))


def _worker_context(worker) -> dict:
    performance_class = getattr(worker, "performance_class", None)
    return {
        "id": worker.id,
        "name": worker.name,
        "role": worker.role,
        "department": worker.department,
        "seniority_level": worker.seniority_level,
        "location": worker.location,
        "proficiency_score": worker.proficiency_score,
        "individual_performance_score": worker.individual_performance_score,
        "tenure_years": worker.tenure_years,
        "composite_score": worker.composite_score,
        "performance_class": performance_class.value if hasattr(performance_class, "value") else performance_class,
        "pagerank_score": worker.pagerank_score,
        "betweenness_centrality": worker.betweenness_centrality,
        "resume_text": worker.resume_text,
        "skills": _list_attr(worker, "skills", "skills_json"),
        "education": _list_attr(worker, "education", "education_json"),
        "certifications": _list_attr(worker, "certifications", "certifications_json"),
        "languages": _list_attr(worker, "languages", "languages_json"),
        "past_projects": _list_attr(worker, "past_projects", "past_projects_json"),
        "achievements_text": worker.achievements_text,
        "availability_notes": worker.availability_notes,
    }


def _group_context(group, is_member: bool, candidate=None) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "project_name": group.project_name,
        "department": group.department,
        "is_current_member": is_member,
        "candidate_status": candidate.status if candidate else None,
        "candidate_target_role": candidate.target_role if candidate else None,
        "candidate_fit_score": candidate.fit_score if candidate else None,
        "candidate_recommendation": candidate.recommendation if candidate else None,
        "baseline_work_quality": group.baseline_work_quality,
        "project_outcome_score": group.project_outcome_score,
        "adjusted_work_quality": group.adjusted_work_quality,
        "open_role_title": group.open_role_title,
        "required_seniority": group.required_seniority,
        "team_context": group.team_context,
        "required_skills": _list_attr(group, "required_skills", "required_skills_json"),
        "preferred_skills": _list_attr(group, "preferred_skills", "preferred_skills_json"),
        "responsibilities": _list_attr(group, "responsibilities", "responsibilities_json"),
        "hiring_notes": group.hiring_notes,
    }


def _relationship_context(worker, workers, relationships) -> dict:
    worker_names = {w.id: w.name for w in workers}
    direct = []
    for rel in relationships:
        if rel.source_id == worker.id:
            other_id = rel.target_id
        elif rel.target_id == worker.id:
            other_id = rel.source_id
        else:
            continue
        direct.append(
            {
                "collaborator": worker_names.get(other_id, other_id),
                "type": rel.rel_type.value if hasattr(rel.rel_type, "value") else str(rel.rel_type),
                "interaction_frequency": rel.interaction_frequency,
                "collaboration_quality": rel.collaboration_quality,
                "weight": rel.weight,
            }
        )
    direct.sort(key=lambda item: item["weight"], reverse=True)
    return {
        "direct_relationship_count": len(direct),
        "top_relationships": direct[:8],
        "mean_relationship_weight": round(mean([d["weight"] for d in direct]), 4) if direct else 0.0,
    }


def evaluate_worker_context(
    worker,
    workers,
    groups,
    relationships,
    memberships: dict[str, list[str]],
    candidates: list,
) -> tuple[WorkerAIEvaluationOut, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIUnavailableError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise OpenAIUnavailableError("openai package is not installed") from exc

    candidate_by_group = {c.group_id: c for c in candidates}
    current_group_ids = {gid for gid, member_ids in memberships.items() if worker.id in member_ids}
    relevant_groups = [
        _group_context(group, group.id in current_group_ids, candidate_by_group.get(group.id))
        for group in groups
        if group.id in current_group_ids or group.id in candidate_by_group
    ]

    payload = {
        "worker": _worker_context(worker),
        "company": {
            "worker_count": len(workers),
            "group_count": len(groups),
            "relationship_count": len(relationships),
            "average_composite_score": round(mean([w.composite_score for w in workers]), 4) if workers else 0.0,
            "departments": sorted({w.department for w in workers}),
        },
        "teams": relevant_groups,
        "network_context": _relationship_context(worker, workers, relationships),
    }

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    schema = _strict_json_schema(WorkerAIEvaluationOut.model_json_schema())
    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Voce avalia um funcionario no contexto da empresa. Use somente as evidencias "
                        "fornecidas, considere desempenho, curriculo, relacoes, equipes atuais e equipes "
                        "em que a pessoa esta sendo cogitada. A avaliacao apoia decisao humana e nao deve "
                        "ser tratada como decisao automatica."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Gere uma avaliacao contextual deste funcionario para a dashboard executiva. "
                        "Destaque contribuicoes, riscos, oportunidades de crescimento e acoes sugeridas.\n\n"
                        f"{json.dumps(payload, ensure_ascii=False)}"
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "worker_context_evaluation",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
    except Exception as exc:
        raise FitEvaluatorError(str(exc)) from exc

    raw = getattr(response, "output_text", None)
    if not raw:
        try:
            raw = response.output[0].content[0].text
        except Exception as exc:
            raise FitEvaluatorError("OpenAI response did not include text output") from exc

    try:
        return WorkerAIEvaluationOut.model_validate_json(raw), model
    except Exception as exc:
        raise FitEvaluatorError("OpenAI response did not match the expected schema") from exc
