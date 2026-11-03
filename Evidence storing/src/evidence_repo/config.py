from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    s3_endpoint_url: str
    s3_bucket: str
    s3_region: str = "us-east-1"
    s3_access_key: str
    s3_secret_key: str
    s3_retention_days: int = 30
    kafka_bootstrap: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    presign_ttl_seconds: int = 60
    log_level: str = "INFO"

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
