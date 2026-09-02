from sqlmodel import SQLModel, create_engine, Session
from ..config import settings

# Initialize SQLite engine
engine = create_engine(settings.resolved_database_url, echo=False)

def init_db():
    """Create tables if they don't exist."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Yield a database session."""
    with Session(engine) as session:
        yield session
