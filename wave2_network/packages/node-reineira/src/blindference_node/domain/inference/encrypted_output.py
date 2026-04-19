from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EncryptedOutput:
    """Vertical-neutral envelope for an inference result.

    The leader produces this by running the model in plaintext on decrypted
    input, then re-encrypting the result as a CoFHE handle bound to the
    on-chain reader's permission (e.g., a Reineira attestor contract).

    Verticals decode the result via vertical-specific `metadata` (e.g.,
    `{"decimals": 4, "modelVersion": 7}`).
    """

    ciphertext_handle: bytes
    model_version: int
    metadata: dict[str, object]

    def __post_init__(self) -> None:
        if len(self.ciphertext_handle) != 32:
            raise ValueError("ciphertext_handle must be exactly 32 bytes (CoFHE handle)")
        if self.model_version <= 0:
            raise ValueError("model_version must be positive")
