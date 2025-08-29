from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://aoidb:aoidb@db:5432/aoidb")
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    api_port: int = int(os.getenv("API_PORT", 8000))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

