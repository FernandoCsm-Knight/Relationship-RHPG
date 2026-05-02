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

    # Populated by the analysis pipeline
    affinity_scores: dict[str, float] = field(default_factory=dict)
    pagerank_score: float = 0.0
    betweenness_centrality: float = 0.0
    composite_score: float = 0.0
    performance_class: Optional[PerformanceClass] = None
