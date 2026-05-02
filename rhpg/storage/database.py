import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(".env.local")
    load_dotenv()

DATABASE_URL = os.getenv("RHPG_DATABASE_URL", "sqlite:///./data/rhpg.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from rhpg.storage.orm_models import WorkerORM, GroupORM, GroupMembershipORM, RelationshipORM, CandidateEvaluationORM  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    planned_columns = {
        "workers": {
            "email": "VARCHAR",
            "location": "VARCHAR",
            "seniority_level": "VARCHAR",
            "resume_text": "TEXT",
            "skills_json": "TEXT DEFAULT '[]'",
            "education_json": "TEXT DEFAULT '[]'",
            "certifications_json": "TEXT DEFAULT '[]'",
            "languages_json": "TEXT DEFAULT '[]'",
            "past_projects_json": "TEXT DEFAULT '[]'",
            "achievements_text": "TEXT",
            "availability_notes": "TEXT",
            "linkedin_url": "VARCHAR",
            "portfolio_url": "VARCHAR",
        },
        "groups": {
            "open_role_title": "VARCHAR",
            "required_seniority": "VARCHAR",
            "team_context": "TEXT",
            "required_skills_json": "TEXT DEFAULT '[]'",
            "preferred_skills_json": "TEXT DEFAULT '[]'",
            "responsibilities_json": "TEXT DEFAULT '[]'",
            "hiring_notes": "TEXT",
        },
    }

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        for table, columns in planned_columns.items():
            if table not in tables:
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
