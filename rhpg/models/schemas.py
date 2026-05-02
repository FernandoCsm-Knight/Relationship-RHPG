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

    model_config = {"from_attributes": True}


# ── Groups ────────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    project_name: str
    department: str
    baseline_work_quality: float = Field(ge=0.0, le=1.0)
    project_outcome_score: float = Field(ge=0.0, le=1.0)
    member_ids: list[str] = Field(default_factory=list)


class GroupOut(BaseModel):
    id: str
    name: str
    project_name: str
    department: str
    baseline_work_quality: float
    project_outcome_score: float
    adjusted_work_quality: float
    member_ids: list[str]

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
