from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    WRITE_POOL_SIZE: int = 10
    WRITE_POOL_OVERFLOW: int = 20
    READ_POOL_SIZE: int = 5
    READ_POOL_OVERFLOW: int = 10
