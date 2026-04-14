from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MONGO_URI: str = "mongodb://localhost:27017/blindference_wave2"
    RPC_URL: str = "http://127.0.0.1:8545"


@lru_cache
def get_settings() -> Settings:
    return Settings()
