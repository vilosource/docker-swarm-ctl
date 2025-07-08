from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import secrets


class Settings(BaseSettings):
    # Application
    app_name: str = "Docker Control Platform"
    app_version: str = "1.0.0"
    debug: bool = Field(False, env="DEBUG")
    
    # API
    api_v1_str: str = "/api/v1"
    
    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: str = Field(
        "postgresql+asyncpg://docker_user:docker_pass@localhost/docker_control",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Docker
    docker_host: Optional[str] = Field(None, env="DOCKER_HOST")
    docker_tls_verify: bool = Field(False, env="DOCKER_TLS_VERIFY")
    docker_cert_path: Optional[str] = Field(None, env="DOCKER_CERT_PATH")
    
    # CORS
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_default: str = Field("100/minute", env="RATE_LIMIT_DEFAULT")
    rate_limit_auth: str = Field("5/minute", env="RATE_LIMIT_AUTH")
    rate_limit_strict: str = Field("10/minute", env="RATE_LIMIT_STRICT")
    rate_limit_relaxed: str = Field("1000/hour", env="RATE_LIMIT_RELAXED")
    rate_limit_container_ops: str = Field("60/minute", env="RATE_LIMIT_CONTAINER_OPS")
    rate_limit_image_ops: str = Field("10/hour", env="RATE_LIMIT_IMAGE_OPS")
    rate_limit_system_ops: str = Field("5/hour", env="RATE_LIMIT_SYSTEM_OPS")
    
    # Celery
    celery_broker_url: str = Field(None, env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(None, env="CELERY_RESULT_BACKEND")
    
    @validator("celery_broker_url", pre=True)
    def set_celery_broker(cls, v, values):
        if v is None and "redis_url" in values:
            return values["redis_url"]
        return v
    
    @validator("celery_result_backend", pre=True)
    def set_celery_backend(cls, v, values):
        if v is None and "redis_url" in values:
            return values["redis_url"]
        return v
    
    # Admin User (for initial setup)
    admin_email: str = Field("admin@localhost.local", env="ADMIN_EMAIL")
    admin_password: str = Field("changeme123", env="ADMIN_PASSWORD")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()