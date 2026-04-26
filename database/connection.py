"""
database.connection
~~~~~~~~~~~~~~~~~~~
SQLAlchemy engine and session factory.  Import from here everywhere.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as _Session

_USER = os.getenv("DB_USER", "fixapp")
_PASS = os.getenv("DB_PASS", "fixpass_2026")
_HOST = os.getenv("DB_HOST", "localhost")
_PORT = os.getenv("DB_PORT", "3306")
_NAME = os.getenv("DB_NAME", "fix_analyzer")

DATABASE_URL = (
    f"mysql+mysqlconnector://{_USER}:{_PASS}@{_HOST}:{_PORT}/{_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

Session = sessionmaker(bind=engine)


def get_session() -> _Session:
    """Return a new session (caller must close / use as context manager)."""
    return Session()
