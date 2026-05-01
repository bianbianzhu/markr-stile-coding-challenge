import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class S(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    WRITE_POOL_SIZE: int = 10
    WRITE_POOL_OVERFLOW: int = 20
    READ_POOL_SIZE: int = 5
    READ_POOL_OVERFLOW: int = 10


os.environ["DATABASE_URL"] = "postgresql+asyncpg://x:x@h/db"
print("loaded:", S().model_dump())

# Missing should fail loudly
os.environ.pop("DATABASE_URL")
try:
    S()
    print("MISSING did not raise")
except Exception as exc:
    print("missing raises:", type(exc).__name__)
