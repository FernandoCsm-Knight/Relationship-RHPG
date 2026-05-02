from uuid import uuid4
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
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
    email = Column(String, nullable=True)
    location = Column(String, nullable=True)
    seniority_level = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)
    skills_json = Column(Text, default="[]")
    education_json = Column(Text, default="[]")
    certifications_json = Column(Text, default="[]")
    languages_json = Column(Text, default="[]")
    past_projects_json = Column(Text, default="[]")
    achievements_text = Column(Text, nullable=True)
    availability_notes = Column(Text, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)

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
    open_role_title = Column(String, nullable=True)
    required_seniority = Column(String, nullable=True)
    team_context = Column(Text, nullable=True)
    required_skills_json = Column(Text, default="[]")
    preferred_skills_json = Column(Text, default="[]")
    responsibilities_json = Column(Text, default="[]")
    hiring_notes = Column(Text, nullable=True)


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


class CandidateEvaluationORM(Base):
    __tablename__ = "candidate_evaluations"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    status = Column(String, default="CONSIDERING", nullable=False)
    target_role = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    fit_score = Column(Float, nullable=True)
    recommendation = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    strengths_json = Column(Text, default="[]")
    risks_json = Column(Text, default="[]")
    skill_matches_json = Column(Text, default="[]")
    skill_gaps_json = Column(Text, default="[]")
    interview_questions_json = Column(Text, default="[]")
    model = Column(String, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
