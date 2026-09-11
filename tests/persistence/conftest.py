import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from market_pipeline.persistence.models import Base


@pytest.fixture(scope="session")
def database_engine() -> Iterator[Engine]:
    database_url = os.environ[
        "MARKET_PIPELINE_TEST_DATABASE_URL"
    ]
    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
            if database_name != "market_pipeline_test":
                raise RuntimeError(
                    "PostgreSQL integration tests require "
                    "the market_pipeline_test database"
                )

        yield engine

    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def database_session(
    database_engine: Engine,
    database_schema: None,
) -> Iterator[Session]:
    with database_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )

        yield session

        session.close()

        transaction.rollback()


@pytest.fixture(scope="session")
def database_schema(
    database_engine: Engine,
) -> Iterator[None]:
    Base.metadata.create_all(database_engine)

    yield None

    Base.metadata.drop_all(database_engine)
