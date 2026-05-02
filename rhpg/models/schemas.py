from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from rhpg.models.worker import PerformanceClass
from rhpg.models.relationship import RelationshipType


# ── Workers ──────────────────────────────────────────────────────────────────

class WorkerCreate(BaseModel):
    name: str
    role: str
    department: str
    proficiency_score: float = Field(ge=0.0, le=1.0)
    individual_performance_score: float = Field(ge=0.0, le=1.0)
    tenure_years: float = Field(ge=0.0, default=0.0)
    email: Optional[str] = None
    location: Optional[str] = None
    seniority_level: Optional[str] = None
    resume_text: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    past_projects: list[str] = Field(default_factory=list)
    achievements_text: Optional[str] = None
    availability_notes: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class WorkerCandidateSummary(BaseModel):
    candidate_id: str
    group_id: str
    group_name: str
    status: str
    target_role: Optional[str] = None
    fit_score: Optional[float] = None
    recommendation: Optional[str] = None


class WorkerOut(BaseModel):
    id: str
    name: str
    role: str
    department: str
    proficiency_score: float
    individual_performance_score: float
    tenure_years: float
    pagerank_score: float
    betweenness_centrality: float
    composite_score: float
    performance_class: Optional[PerformanceClass]
    email: Optional[str] = None
    location: Optional[str] = None
    seniority_level: Optional[str] = None
    resume_text: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    past_projects: list[str] = Field(default_factory=list)
    achievements_text: Optional[str] = None
    availability_notes: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    candidates: list[WorkerCandidateSummary] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Groups ────────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    project_name: str
    department: str
    baseline_work_quality: float = Field(ge=0.0, le=1.0)
    project_outcome_score: float = Field(ge=0.0, le=1.0)
    member_ids: list[str] = Field(default_factory=list)
    open_role_title: Optional[str] = None
    required_seniority: Optional[str] = None
    team_context: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    hiring_notes: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    project_name: Optional[str] = None
    department: Optional[str] = None
    baseline_work_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    project_outcome_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    open_role_title: Optional[str] = None
    required_seniority: Optional[str] = None
    team_context: Optional[str] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    responsibilities: Optional[list[str]] = None
    hiring_notes: Optional[str] = None


class GroupOut(BaseModel):
    id: str
    name: str
    project_name: str
    department: str
    baseline_work_quality: float
    project_outcome_score: float
    adjusted_work_quality: float
    member_ids: list[str]
    open_role_title: Optional[str] = None
    required_seniority: Optional[str] = None
    team_context: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    hiring_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class GroupQualityOut(BaseModel):
    group_id: str
    baseline_work_quality: float
    adjusted_work_quality: float


# ── Relationships ─────────────────────────────────────────────────────────────

class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    rel_type: RelationshipType
    interaction_frequency: float = Field(ge=0.0, le=1.0)
    collaboration_quality: float = Field(ge=0.0, le=1.0)


class RelationshipOut(BaseModel):
    id: str
    source_id: str
    target_id: str
    rel_type: RelationshipType
    interaction_frequency: float
    collaboration_quality: float
    weight: float

    model_config = {"from_attributes": True}


# ── Analysis ──────────────────────────────────────────────────────────────────

class WorkerAnalysisResult(BaseModel):
    worker_id: str
    name: str
    role: str
    department: str
    composite_score: float
    performance_class: PerformanceClass
    pagerank_score: float
    betweenness_centrality: float
    affinity_scores: dict[str, float]
    delta_contributions: dict[str, float]


class ClassifyRequest(BaseModel):
    weights: dict[str, float] = Field(
        default={
            "individual_performance": 0.30,
            "proficiency": 0.15,
            "pagerank": 0.20,
            "betweenness": 0.10,
            "mean_affinity": 0.10,
            "mean_delta": 0.15,
        }
    )
    method: str = Field(default="percentile", pattern="^(percentile|threshold|kmeans)$")
    high_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    low_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    n_clusters: int = Field(default=3, ge=2, le=10)


class LeaderboardEntry(BaseModel):
    rank: int
    worker_id: str
    name: str
    role: str
    department: str
    composite_score: float
    performance_class: PerformanceClass


# ── Candidates / AI Fit Evaluation ───────────────────────────────────────────

class CandidateCreate(BaseModel):
    worker_id: str
    group_id: str
    status: str = Field(default="CONSIDERING")
    target_role: Optional[str] = None
    notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    status: Optional[str] = None
    target_role: Optional[str] = None
    notes: Optional[str] = None


class CandidateAIEvaluationOut(BaseModel):
    fit_score: float = Field(ge=0.0, le=1.0)
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    skill_matches: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)


class CandidateOut(BaseModel):
    id: str
    worker_id: str
    worker_name: str
    group_id: str
    group_name: str
    status: str
    target_role: Optional[str] = None
    notes: Optional[str] = None
    fit_score: Optional[float] = None
    recommendation: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    skill_matches: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    model: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkerAIEvaluationOut(BaseModel):
    overall_score: float = Field(ge=0.0, le=1.0)
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    company_context_assessment: str
    team_context_assessment: str
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    growth_opportunities: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
