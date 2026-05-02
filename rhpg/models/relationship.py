from dataclasses import dataclass
from enum import Enum


class RelationshipType(str, Enum):
    COLLABORATION = "COLLABORATION"
    MEMBERSHIP = "MEMBERSHIP"
    CROSS_GROUP = "CROSS_GROUP"


@dataclass
class Relationship:
    id: str
    source_id: str
    target_id: str
    rel_type: RelationshipType
    interaction_frequency: float
    collaboration_quality: float
    weight: float = 0.0

    def __post_init__(self) -> None:
        self.weight = round(self.interaction_frequency * self.collaboration_quality, 4)
