from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    # Primary database URL
    database_url: str = os.getenv("DATABASE_URL", "postgresql://aoidb:aoidb@db:5432/aoidb")

    # Redis configuration
    redis_host: str = os.getenv("REDIS_HOST", os.getenv("REDIS_URL", "redis://redis:6379").split("://")[-1].split(":")[0])
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_url: str = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}")

    # Qdrant configuration
    qdrant_host: str = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_url: str = os.getenv("QDRANT_URL", f"http://{os.getenv('QDRANT_HOST', 'qdrant')}:{os.getenv('QDRANT_PORT', '6333')}")

    # API settings
    api_port: int = int(os.getenv("API_PORT", 8000))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
