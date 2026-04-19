from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EncryptedInput:
    """Vertical-neutral envelope for an inference input.

    `ciphertext_handle` is the CoFHE handle that authorized executors decrypt.
    `permission_grant_id` references the on-chain CoFHE grant that authorizes
    decryption by the permitted executor set.

    Verticals attach domain-specific schema in `metadata` (e.g.,
    `{"input_type": "borrower-history", "schema_version": 3}`).
    """

    ciphertext_handle: bytes
    permission_grant_id: bytes
    sealed_at_epoch: int
    metadata: dict[str, object]

    def __post_init__(self) -> None:
        if not self.ciphertext_handle:
            raise ValueError("ciphertext_handle must be non-empty")
        if not self.permission_grant_id:
            raise ValueError("permission_grant_id must be non-empty")
