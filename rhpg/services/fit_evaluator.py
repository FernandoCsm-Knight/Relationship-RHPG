import json
import os

from rhpg.models.schemas import CandidateAIEvaluationOut
from rhpg.storage.repository import load_json_list

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


class FitEvaluatorError(RuntimeError):
    pass


class OpenAIUnavailableError(FitEvaluatorError):
    pass


def _strict_json_schema(schema: dict) -> dict:
    """Make Pydantic's schema compatible with OpenAI strict structured outputs."""
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        properties = schema.get("properties", {})
        if properties:
            schema["required"] = list(properties.keys())
    for value in schema.get("properties", {}).values():
        if isinstance(value, dict):
            _strict_json_schema(value)
    for value in schema.get("$defs", {}).values():
        if isinstance(value, dict):
            _strict_json_schema(value)
    items = schema.get("items")
    if isinstance(items, dict):
        _strict_json_schema(items)
    return schema


def _worker_context(worker) -> dict:
    return {
        "name": worker.name,
        "role": worker.role,
        "department": worker.department,
        "seniority_level": worker.seniority_level,
        "location": worker.location,
        "proficiency_score": worker.proficiency_score,
        "individual_performance_score": worker.individual_performance_score,
        "tenure_years": worker.tenure_years,
        "composite_score": worker.composite_score,
        "performance_class": worker.performance_class,
        "pagerank_score": worker.pagerank_score,
        "betweenness_centrality": worker.betweenness_centrality,
        "resume_text": worker.resume_text,
        "skills": load_json_list(worker.skills_json),
        "education": load_json_list(worker.education_json),
        "certifications": load_json_list(worker.certifications_json),
        "languages": load_json_list(worker.languages_json),
        "past_projects": load_json_list(worker.past_projects_json),
        "achievements_text": worker.achievements_text,
        "availability_notes": worker.availability_notes,
        "linkedin_url": worker.linkedin_url,
        "portfolio_url": worker.portfolio_url,
    }


def _group_context(group) -> dict:
    return {
        "name": group.name,
        "project_name": group.project_name,
        "department": group.department,
        "baseline_work_quality": group.baseline_work_quality,
        "project_outcome_score": group.project_outcome_score,
        "adjusted_work_quality": group.adjusted_work_quality,
        "open_role_title": group.open_role_title,
        "required_seniority": group.required_seniority,
        "team_context": group.team_context,
        "required_skills": load_json_list(group.required_skills_json),
        "preferred_skills": load_json_list(group.preferred_skills_json),
        "responsibilities": load_json_list(group.responsibilities_json),
        "hiring_notes": group.hiring_notes,
    }


def evaluate_candidate_fit(worker, group, candidate) -> tuple[CandidateAIEvaluationOut, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIUnavailableError("OPENAI_API_KEY is not configured")

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    payload = {
        "candidate": {
            "target_role": candidate.target_role,
            "notes": candidate.notes,
            "status": candidate.status,
        },
        "worker": _worker_context(worker),
        "team": _group_context(group),
    }

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise OpenAIUnavailableError("openai package is not installed") from exc

    client = OpenAI(api_key=api_key)
    schema = _strict_json_schema(CandidateAIEvaluationOut.model_json_schema())
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Voce avalia encaixe funcionario-equipe para apoiar decisao humana. "
                        "Seja objetivo, use apenas as evidencias fornecidas, nao tome decisao final "
                        "e retorne somente JSON valido no schema solicitado."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Avalie se esta pessoa sera uma boa adicao para a equipe. "
                        "Considere curriculo, projetos, skills, score atual, contexto da equipe, "
                        "riscos e lacunas.\n\n"
                        f"{json.dumps(payload, ensure_ascii=False)}"
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "candidate_fit_evaluation",
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
        return CandidateAIEvaluationOut.model_validate_json(raw), model
    except Exception as exc:
        raise FitEvaluatorError("OpenAI response did not match the expected schema") from exc
