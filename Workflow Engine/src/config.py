from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # The monorepo root .env also contains CTEM SMTP values. Ignore settings
    # owned by sibling services so Workflow can share that local env file.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/workflow"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    service_name: str = "workflow-service"
    idempotency_ttl: int = 3600
    default_retry_count: int = 3
    default_backoff: str = "exponential"

@lru_cache
def get_settings():
    return Settings()
