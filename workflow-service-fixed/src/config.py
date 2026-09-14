from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/workflow"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    service_name: str = "workflow-service"
    idempotency_ttl: int = 3600
    default_retry_count: int = 3
    default_backoff: str = "exponential"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
