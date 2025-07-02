from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    auth_method: str = "static"
    static_token_secret: str = "dev-secret-token"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
