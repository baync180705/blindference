from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class NodeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BLINDFERENCE_NODE_", env_file=".env", extra="ignore")

    icl_base_url: str = "http://localhost:8000"
    provider: str = "groq"
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    poll_interval_seconds: int = Field(default=5, ge=1, le=300)
    confidence_floor: int = Field(default=78, ge=1, le=100)
    mock_cloud_inference: bool = True
    max_iterations: int = Field(default=0, ge=0)
    cofhe_rpc_url: str = "http://127.0.0.1:8545"
    cofhe_chain_id: int = 421614
    operator_private_key: str | None = None
    cofhe_bridge_script: str = str(Path(__file__).resolve().parents[2] / "scripts" / "cofhe_bridge.mjs")
