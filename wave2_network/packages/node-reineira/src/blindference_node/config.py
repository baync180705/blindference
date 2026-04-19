from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NodeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BLINDFERENCE_NODE_", env_file=".env", extra="ignore")

    icl_base_url: str = "http://localhost:8000"
    provider: str = "groq"
    groq_model: str = "llama3-70b-8192"
    gemini_model: str = "gemini-1.5-pro"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    poll_interval_seconds: int = Field(default=5, ge=1, le=300)
    confidence_floor: int = Field(default=78, ge=1, le=100)
    mock_cloud_inference: bool = True
    max_iterations: int = Field(default=0, ge=0)
