import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/modelwatch_test"

engine = create_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    join_transaction_mode="create_savepoint",
)


@pytest.fixture()
def db_session():
    """
    Real-PostgreSQL session for integration tests. Each test runs inside a
    transaction that is rolled back afterwards, so tests stay isolated
    without needing to recreate the schema per test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
