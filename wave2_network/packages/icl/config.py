from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DEMO_OPERATOR_KEYS = ",".join(
    [
        "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    ]
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "blindference_wave2"
    ARBITRUM_SEPOLIA_RPC: str = "http://127.0.0.1:8545"
    NODE_ATTESTATION_REGISTRY_ADDRESS: str = "0x0000000000000000000000000000000000000000"
    EXECUTION_COMMITMENT_REGISTRY_ADDRESS: str = "0x0000000000000000000000000000000000000000"
    AGENT_CONFIG_REGISTRY_ADDRESS: str = "0x0000000000000000000000000000000000000000"
    REPUTATION_REGISTRY_ADDRESS: str = "0x0000000000000000000000000000000000000000"
    REWARD_ACCUMULATOR_ADDRESS: str = "0x0000000000000000000000000000000000000000"
    ICL_SERVICE_PRIVATE_KEY: str = (
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    MOCK_CHAIN: bool = False
    DEFAULT_MIN_TIER: int = 1
    DEFAULT_VERIFIER_COUNT: int = 2
    HEARTBEAT_GRACE_SECONDS: int = 120
    EXECUTION_COMMIT_WINDOW_SECONDS: int = 600
    EXECUTION_REVEAL_WINDOW_SECONDS: int = 600
    DEMO_OPERATOR_PRIVATE_KEYS: str = DEFAULT_DEMO_OPERATOR_KEYS

    @property
    def packages_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def contracts_dir(self) -> Path:
        return self.packages_dir / "contracts"

    @property
    def contracts_out_dir(self) -> Path:
        return self.contracts_dir / "out"

    @property
    def demo_operator_private_keys(self) -> list[str]:
        return [
            private_key.strip()
            for private_key in self.DEMO_OPERATOR_PRIVATE_KEYS.split(",")
            if private_key.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
