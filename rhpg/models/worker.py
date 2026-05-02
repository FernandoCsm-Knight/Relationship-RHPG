from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PerformanceClass(str, Enum):
    HIGH = "HIGH"
    NEUTRAL = "NEUTRAL"
    LOW = "LOW"


@dataclass
class Worker:
    id: str
    name: str
    role: str
    department: str
    proficiency_score: float
    individual_performance_score: float
    tenure_years: float = 0.0
    email: Optional[str] = None
    location: Optional[str] = None
    seniority_level: Optional[str] = None
    resume_text: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    past_projects: list[str] = field(default_factory=list)
    achievements_text: Optional[str] = None
    availability_notes: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    # Populated by the analysis pipeline
    affinity_scores: dict[str, float] = field(default_factory=dict)
    pagerank_score: float = 0.0
    betweenness_centrality: float = 0.0
    composite_score: float = 0.0
    performance_class: Optional[PerformanceClass] = None
