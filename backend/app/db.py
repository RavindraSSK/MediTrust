from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url

engine_kwargs: dict = {"pool_pre_ping": True}
if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    logger.info("Using SQLite database at %s", DATABASE_URL)

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
