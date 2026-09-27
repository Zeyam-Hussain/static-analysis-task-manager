"""Database engine, ORM base, and request-scoped sessions."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..core.config import settings


DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)

session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session and always close it after the request."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
