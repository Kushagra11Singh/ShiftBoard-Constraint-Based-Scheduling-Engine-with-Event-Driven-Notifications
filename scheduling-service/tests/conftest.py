import os
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DB_URL = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://shiftboard:shiftboard123@localhost:5432/shiftboard_test',
)

_engine = create_engine(TEST_DB_URL)
Base.metadata.drop_all(_engine)
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope='function')
def db():
    session = _TestSession()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(sa.text(f'TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE'))
    session.commit()
    session.close()


@pytest.fixture(scope='function')
def client(db: Session):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
