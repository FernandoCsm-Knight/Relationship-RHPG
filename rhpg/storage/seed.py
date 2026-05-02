"""
Populate the database with synthetic data for development and testing.
Run: python -m rhpg.storage.seed
"""
import random
from uuid import uuid4

from rhpg.storage.database import init_db, SessionLocal
from rhpg.storage.repository import WorkerRepository, GroupRepository, RelationshipRepository
from rhpg.models.schemas import WorkerCreate, GroupCreate, RelationshipCreate
from rhpg.models.relationship import RelationshipType

random.seed(42)

ROLES = ["Engineer", "Designer", "Product Manager", "Data Analyst", "QA Engineer", "Tech Lead"]
DEPARTMENTS = ["Engineering", "Design", "Product", "Data", "QA"]

WORKER_NAMES = [
    "Alice Ferreira", "Bruno Santos", "Carla Oliveira", "Diego Lima", "Elena Souza",
    "Felipe Costa", "Gabriela Rocha", "Henrique Alves", "Isabela Nunes", "João Pereira",
    "Karen Martins", "Lucas Mendes", "Mariana Silva", "Nicolas Cardoso", "Olivia Ribeiro",
    "Paulo Moreira", "Queila Barbosa", "Rafael Gomes", "Sabrina Freitas", "Thiago Carvalho",
    "Úrsula Dias", "Vitor Nascimento", "Wanda Cruz", "Xavier Teixeira", "Yasmin Monteiro",
]

PROJECTS = [
    ("Alpha Squad", "Project Alpha", "Engineering"),
    ("Beta Core", "Project Beta", "Product"),
    ("Gamma UX", "Project Gamma", "Design"),
    ("Delta Analytics", "Project Delta", "Data"),
    ("Epsilon QA", "Project Epsilon", "QA"),
]


def seed() -> None:
    init_db()
    db = SessionLocal()

    worker_repo = WorkerRepository(db)
    group_repo = GroupRepository(db)
    rel_repo = RelationshipRepository(db)

    # Clear existing data
    from rhpg.storage.orm_models import WorkerORM, GroupORM, GroupMembershipORM, RelationshipORM
    db.query(RelationshipORM).delete()
    db.query(GroupMembershipORM).delete()
    db.query(GroupORM).delete()
    db.query(WorkerORM).delete()
    db.commit()

    # Create workers
    workers = []
    for name in WORKER_NAMES:
        w = worker_repo.create(WorkerCreate(
            name=name,
            role=random.choice(ROLES),
            department=random.choice(DEPARTMENTS),
            proficiency_score=round(random.uniform(0.3, 1.0), 2),
            individual_performance_score=round(random.uniform(0.2, 1.0), 2),
            tenure_years=round(random.uniform(0.5, 8.0), 1),
        ))
        workers.append(w)
    print(f"Created {len(workers)} workers")

    # Create groups — assign 5-7 random workers per group
    groups = []
    for name, project, dept in PROJECTS:
        size = random.randint(5, 7)
        member_ids = [w.id for w in random.sample(workers, size)]
        g = group_repo.create(GroupCreate(
            name=name,
            project_name=project,
            department=dept,
            baseline_work_quality=round(random.uniform(0.4, 0.85), 2),
            project_outcome_score=round(random.uniform(0.4, 0.9), 2),
            member_ids=member_ids,
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
    db.close()
    print("Seed complete.")


if __name__ == "__main__":
    seed()
