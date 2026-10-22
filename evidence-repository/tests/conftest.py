
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool

# Test environment configuration for running pytest on Windows
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://evidence:evidence@localhost:5432/evidence",
)
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:4566")
os.environ.setdefault("S3_BUCKET", "evidence")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")
os.environ.setdefault("KAFKA_BOOTSTRAP", "localhost:9092")
os.environ.setdefault("JWT_SECRET", "test-secret")

from evidence_repo.auth import mint_dev_token  # noqa: E402
from evidence_repo.main import app  # noqa: E402
from evidence_repo.events import stop_producer  # noqa: E402
from evidence_repo import db  # noqa: E402


# Prevent async database connections from being reused
# across different pytest event loops.
db._engine = None
db._sessionmaker = None

_original_get_engine = db.create_async_engine


def test_create_async_engine(*args, **kwargs):
    kwargs["poolclass"] = NullPool
    return _original_get_engine(*args, **kwargs)


db.create_async_engine = test_create_async_engine


@pytest.fixture
def tenant_id() -> uuid.UUID:
    # Give each test its own evidence chain.
    return uuid.uuid4()


@pytest.fixture(scope="session")
def user_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def token(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    return mint_dev_token(
        str(tenant_id),
        str(user_id),
    )


@pytest_asyncio.fixture(loop_scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            yield c
    finally:
        # Stop Kafka after the test, while the fixture's
        # event loop is still available.
        await stop_producer()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

