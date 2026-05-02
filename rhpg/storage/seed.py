"""
Populate the database with synthetic data for development and testing.
Run: python -m rhpg.storage.seed
"""
import random
from uuid import uuid4

from rhpg.storage.database import init_db, SessionLocal
from rhpg.storage.repository import WorkerRepository, GroupRepository, RelationshipRepository, CandidateRepository
from rhpg.models.schemas import WorkerCreate, GroupCreate, RelationshipCreate, CandidateCreate
from rhpg.models.relationship import RelationshipType

random.seed(42)

ROLES = ["Engineer", "Designer", "Product Manager", "Data Analyst", "QA Engineer", "Tech Lead"]
DEPARTMENTS = ["Engineering", "Design", "Product", "Data", "QA"]
SENIORITIES = ["Junior", "Mid-level", "Senior", "Staff", "Lead"]
LOCATIONS = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Remoto"]

ROLE_SKILLS = {
    "Engineer": ["Python", "APIs", "SQL", "Docker", "Observability", "System Design"],
    "Designer": ["UX Research", "Figma", "Design Systems", "Prototyping", "Accessibility"],
    "Product Manager": ["Roadmap", "Discovery", "Metrics", "Stakeholder Management", "Prioritization"],
    "Data Analyst": ["SQL", "Python", "Dashboards", "Statistics", "Experimentation"],
    "QA Engineer": ["Test Automation", "Regression Testing", "Cypress", "Quality Strategy", "CI"],
    "Tech Lead": ["Architecture", "Mentoring", "Code Review", "Delivery Planning", "Incident Response"],
}

PROJECT_TEMPLATES = [
    "Led delivery of a customer-facing dashboard with weekly executive reporting.",
    "Improved deployment reliability by reducing failed releases and documenting runbooks.",
    "Built integrations between internal systems and product analytics tools.",
    "Coordinated a cross-functional initiative with design, engineering, and product.",
    "Automated repetitive operational checks and reduced manual review time.",
    "Supported migration of legacy workflows to a clearer, metrics-driven process.",
]

WORKER_NAMES = [
    "Alice Ferreira", "Bruno Santos", "Carla Oliveira", "Diego Lima", "Elena Souza",
    "Felipe Costa", "Gabriela Rocha", "Henrique Alves", "Isabela Nunes", "João Pereira",
    "Karen Martins", "Lucas Mendes", "Mariana Silva", "Nicolas Cardoso", "Olivia Ribeiro",
    "Paulo Moreira", "Queila Barbosa", "Rafael Gomes", "Sabrina Freitas", "Thiago Carvalho",
    "Úrsula Dias", "Vitor Nascimento", "Wanda Cruz", "Xavier Teixeira", "Yasmin Monteiro",
]

PROJECTS = [
    (
        "Alpha Squad",
        "Project Alpha",
        "Engineering",
        "Backend Engineer",
        "Senior",
        ["Python", "APIs", "System Design"],
        ["Observability", "Docker"],
        ["Design reliable APIs", "Review technical tradeoffs", "Improve platform resilience"],
    ),
    (
        "Beta Core",
        "Project Beta",
        "Product",
        "Product Manager",
        "Mid-level",
        ["Roadmap", "Discovery", "Metrics"],
        ["Stakeholder Management", "Prioritization"],
        ["Shape product bets", "Coordinate delivery", "Track adoption metrics"],
    ),
    (
        "Gamma UX",
        "Project Gamma",
        "Design",
        "Product Designer",
        "Mid-level",
        ["Figma", "UX Research", "Design Systems"],
        ["Accessibility", "Prototyping"],
        ["Map user journeys", "Prototype flows", "Maintain design consistency"],
    ),
    (
        "Delta Analytics",
        "Project Delta",
        "Data",
        "Data Analyst",
        "Senior",
        ["SQL", "Python", "Dashboards"],
        ["Statistics", "Experimentation"],
        ["Build decision dashboards", "Analyze performance trends", "Design experiments"],
    ),
    (
        "Epsilon QA",
        "Project Epsilon",
        "QA",
        "QA Engineer",
        "Mid-level",
        ["Test Automation", "Regression Testing", "CI"],
        ["Cypress", "Quality Strategy"],
        ["Expand automated coverage", "Improve release confidence", "Document quality risks"],
    ),
]


def _sample_profile(role: str) -> tuple[list[str], list[str], str, str]:
    skills = random.sample(ROLE_SKILLS[role], k=min(4, len(ROLE_SKILLS[role])))
    projects = random.sample(PROJECT_TEMPLATES, 2)
    resume = (
        f"Professional focused on {role.lower()} work with experience in "
        f"{', '.join(skills[:3])}. Has contributed to cross-functional projects, "
        "collaborated with multiple teams, and delivered measurable improvements."
    )
    achievements = random.choice([
        "Recognized for improving team delivery predictability.",
        "Mentored peers and documented reusable practices.",
        "Helped reduce operational friction in a critical workflow.",
        "Presented project outcomes to leadership with clear metrics.",
    ])
    return skills, projects, resume, achievements


def seed() -> None:
    init_db()
    db = SessionLocal()

    worker_repo = WorkerRepository(db)
    group_repo = GroupRepository(db)
    rel_repo = RelationshipRepository(db)
    candidate_repo = CandidateRepository(db)

    # Clear existing data
    from rhpg.storage.orm_models import WorkerORM, GroupORM, GroupMembershipORM, RelationshipORM, CandidateEvaluationORM
    db.query(CandidateEvaluationORM).delete()
    db.query(RelationshipORM).delete()
    db.query(GroupMembershipORM).delete()
    db.query(GroupORM).delete()
    db.query(WorkerORM).delete()
    db.commit()

    # Create workers
    workers = []
    for idx, name in enumerate(WORKER_NAMES):
        role = random.choice(ROLES)
        skills, projects, resume, achievements = _sample_profile(role)
        w = worker_repo.create(WorkerCreate(
            name=name,
            role=role,
            department=random.choice(DEPARTMENTS),
            proficiency_score=round(random.uniform(0.3, 1.0), 2),
            individual_performance_score=round(random.uniform(0.2, 1.0), 2),
            tenure_years=round(random.uniform(0.5, 8.0), 1),
            email=f"{name.lower().replace(' ', '.')}@example.com",
            location=random.choice(LOCATIONS),
            seniority_level=random.choice(SENIORITIES),
            resume_text=resume,
            skills=skills,
            education=random.sample([
                "BSc Computer Science",
                "MBA Product Management",
                "Design Strategy Certificate",
                "Data Analytics Specialization",
                "Software Engineering Bootcamp",
            ], 2),
            certifications=random.sample([
                "Scrum Fundamentals",
                "AWS Cloud Practitioner",
                "Google Analytics",
                "ISTQB Foundation",
                "UX Research Methods",
            ], 2),
            languages=random.sample(["Portuguese", "English", "Spanish"], 2),
            past_projects=projects,
            achievements_text=achievements,
            availability_notes=random.choice([
                "Available for allocation next sprint.",
                "Can support part-time during transition.",
                "Prefers remote collaboration.",
                "Available after current project handoff.",
            ]),
            linkedin_url=f"https://linkedin.com/in/{idx}-{name.lower().replace(' ', '-')}",
            portfolio_url=f"https://portfolio.example.com/{idx}",
        ))
        workers.append(w)
    print(f"Created {len(workers)} workers")

    # Create groups — assign 5-7 random workers per group
    groups = []
    for name, project, dept, open_role, seniority, required, preferred, responsibilities in PROJECTS:
        size = random.randint(5, 7)
        member_ids = [w.id for w in random.sample(workers, size)]
        g = group_repo.create(GroupCreate(
            name=name,
            project_name=project,
            department=dept,
            baseline_work_quality=round(random.uniform(0.4, 0.85), 2),
            project_outcome_score=round(random.uniform(0.4, 0.9), 2),
            member_ids=member_ids,
            open_role_title=open_role,
            required_seniority=seniority,
            team_context=(
                f"{name} is looking for support on {project}. The team needs someone "
                "who can contribute quickly, collaborate well, and close current capability gaps."
            ),
            required_skills=required,
            preferred_skills=preferred,
            responsibilities=responsibilities,
            hiring_notes="Prioritize practical experience, collaboration history, and evidence of delivery.",
        ))
        groups.append((g, member_ids))
    print(f"Created {len(groups)} groups")

    # Create collaboration relationships between workers
    rel_count = 0
    all_worker_ids = [w.id for w in workers]
    for g, member_ids in groups:
        # Dense intra-group collaboration
        for i, src in enumerate(member_ids):
            for tgt in member_ids[i + 1:]:
                if random.random() < 0.75:
                    rel_repo.create(RelationshipCreate(
                        source_id=src,
                        target_id=tgt,
                        rel_type=RelationshipType.COLLABORATION,
                        interaction_frequency=round(random.uniform(0.3, 1.0), 2),
                        collaboration_quality=round(random.uniform(0.2, 1.0), 2),
                    ))
                    rel_count += 1

    # Sparse cross-group relationships
    for _ in range(20):
        src, tgt = random.sample(all_worker_ids, 2)
        rel_repo.create(RelationshipCreate(
            source_id=src,
            target_id=tgt,
            rel_type=RelationshipType.CROSS_GROUP,
            interaction_frequency=round(random.uniform(0.1, 0.5), 2),
            collaboration_quality=round(random.uniform(0.2, 0.8), 2),
        ))
        rel_count += 1

    print(f"Created {rel_count} relationships")

    candidate_count = 0
    for group, member_ids in groups:
        available_workers = [w for w in workers if w.id not in member_ids]
        for worker in random.sample(available_workers, k=3):
            candidate_repo.create(CandidateCreate(
                worker_id=worker.id,
                group_id=group.id,
                status=random.choice(["CONSIDERING", "SHORTLISTED", "CONSIDERING"]),
                target_role=group.open_role_title,
                notes=random.choice([
                    "Suggested by manager review.",
                    "Relevant prior project experience.",
                    "Potential transfer candidate.",
                    "Worth evaluating for upcoming squad opening.",
                ]),
            ))
            candidate_count += 1
    print(f"Created {candidate_count} candidate evaluations")
    db.close()
    print("Seed complete.")


if __name__ == "__main__":
    seed()
