from dataclasses import dataclass, field


@dataclass
class Group:
    id: str
    name: str
    project_name: str
    department: str
    baseline_work_quality: float
    project_outcome_score: float
    size: int = 0

    # Populated after delta scoring
    member_ids: list[str] = field(default_factory=list)
    adjusted_work_quality: float = 0.0
