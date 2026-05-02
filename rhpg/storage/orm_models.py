from uuid import uuid4
from sqlalchemy import Column, String, Float, ForeignKey
from rhpg.storage.database import Base


class WorkerORM(Base):
    __tablename__ = "workers"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=False)
    proficiency_score = Column(Float, nullable=False)
    individual_performance_score = Column(Float, nullable=False)
    tenure_years = Column(Float, default=0.0)

    # Computed by analysis pipeline
    pagerank_score = Column(Float, default=0.0)
    betweenness_centrality = Column(Float, default=0.0)
    composite_score = Column(Float, default=0.0)
    performance_class = Column(String, nullable=True)


class GroupORM(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    baseline_work_quality = Column(Float, nullable=False)
    project_outcome_score = Column(Float, nullable=False)
    adjusted_work_quality = Column(Float, default=0.0)


class GroupMembershipORM(Base):
    __tablename__ = "group_memberships"

    worker_id = Column(String, ForeignKey("workers.id"), primary_key=True)
    group_id = Column(String, ForeignKey("groups.id"), primary_key=True)


class RelationshipORM(Base):
    __tablename__ = "relationships"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    source_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    rel_type = Column(String, nullable=False)
    interaction_frequency = Column(Float, default=0.0)
    collaboration_quality = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)
