import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
