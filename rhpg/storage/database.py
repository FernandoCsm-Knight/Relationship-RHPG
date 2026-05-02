import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("RHPG_DATABASE_URL", "sqlite:///./data/rhpg.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from rhpg.storage.orm_models import WorkerORM, GroupORM, GroupMembershipORM, RelationshipORM  # noqa: F401
    Base.metadata.create_all(bind=engine)
