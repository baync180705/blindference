from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class NodeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BLINDFERENCE_NODE_", env_file=".env", extra="ignore")

    icl_base_url: str = "http://localhost:8000"
    provider: str = "groq"
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("BLINDFERENCE_NODE_LLM_MODEL", "LLM_MODEL"),
    )
    llm_base_url: str = Field(
        default="http://localhost:11434/v1",
        validation_alias=AliasChoices("BLINDFERENCE_NODE_LLM_BASE_URL", "LLM_BASE_URL"),
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BLINDFERENCE_NODE_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    confidence_floor: int = Field(default=78, ge=1, le=100)
    mock_cloud_inference: bool = True
    mock_cofhe_decrypt: bool = False
    max_iterations: int = Field(default=0, ge=0)
    rpc_url: str = Field(
        default="http://127.0.0.1:8545",
        validation_alias=AliasChoices(
            "BLINDFERENCE_NODE_RPC_URL",
            "ARBITRUM_SEPOLIA_RPC",
            "BLINDFERENCE_NODE_COFHE_RPC_URL",
        ),
    )
    cofhe_chain_id: int = 421614
    prompt_key_store_address: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BLINDFERENCE_NODE_PROMPT_KEY_STORE_ADDRESS", "PROMPT_KEY_STORE_ADDRESS"),
    )
    operator_private_key: str | None = None
    cofhe_bridge_script: str = str(Path(__file__).resolve().parents[2] / "scripts" / "cofhe_bridge.mjs")
    callback_host: str = "127.0.0.1"
    callback_port: int = Field(default=9101, ge=1, le=65535)
    callback_public_url: str | None = None
    text_stub_prompt_key_hex: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BLINDFERENCE_NODE_TEXT_STUB_PROMPT_KEY_HEX", "TEXT_STUB_PROMPT_KEY_HEX"),
    )
