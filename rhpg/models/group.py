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
    open_role_title: str | None = None
    required_seniority: str | None = None
    team_context: str | None = None
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    hiring_notes: str | None = None

    # Populated after delta scoring
    member_ids: list[str] = field(default_factory=list)
    adjusted_work_quality: float = 0.0
