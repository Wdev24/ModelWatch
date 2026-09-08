import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/modelwatch_test"

_engine = create_engine(TEST_DATABASE_URL, future=True)
_TestSessionLocal = sessionmaker(
    bind=_engine,
    autoflush=False,
    autocommit=False,
    future=True,
    join_transaction_mode="create_savepoint",
)


@pytest.fixture()
def db_session():
    """
    Real-PostgreSQL session wrapped in an outer transaction that is always
    rolled back. join_transaction_mode="create_savepoint" means route-level
    db.commit() calls only release a SAVEPOINT rather than ending the outer
    transaction, so tests stay isolated even though the code under test
    calls commit() for real.
    """
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
