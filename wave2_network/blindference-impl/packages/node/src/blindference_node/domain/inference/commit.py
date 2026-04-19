from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from eth_utils import keccak

from blindference_node.domain.inference.encrypted_output import EncryptedOutput
from blindference_node.domain.shared_kernel.ids import NodeAddress


class ExecutionRole(IntEnum):
    """Wire-compatible with on-chain `IExecutionCommitmentRegistry.Role`."""

    EXECUTOR = 0
    CROSS_VERIFIER = 1


class CommitMismatch(Exception):
    """Raised when a reveal does not match its prior commit, or when executor
    and cross-verifier reveal disagreeing outputs."""


def _address_bytes(node: NodeAddress) -> bytes:
    return bytes.fromhex(node.value[2:])


def compute_commit_digest(
    *,
    role: ExecutionRole,
    node: NodeAddress,
    output_handle: bytes,
    salt: bytes,
) -> bytes:
    """Matches `keccak256(abi.encodePacked(uint8 role, address, bytes32, bytes32))`."""
    if len(output_handle) != 32:
        raise ValueError("output_handle must be 32 bytes")
    if len(salt) != 32:
        raise ValueError("salt must be 32 bytes")
    return keccak(bytes([int(role)]) + _address_bytes(node) + output_handle + salt)


@dataclass(frozen=True, slots=True)
class ExecutionCommit:
    """Hash commitment to an inference output, posted before reveal.

    Wire format matches on-chain `ExecutionCommitmentRegistry.commitDigest(...)`:
    ``keccak256(abi.encodePacked(uint8 role, address node, bytes32 handle, bytes32 salt))``.
    """

    role: ExecutionRole
    node: NodeAddress
    digest: bytes

    def __post_init__(self) -> None:
        if len(self.digest) != 32:
            raise ValueError("commit digest must be 32 bytes")


@dataclass(frozen=True, slots=True)
class ExecutionReveal:
    """Reveal for a prior `ExecutionCommit`."""

    role: ExecutionRole
    node: NodeAddress
    output: EncryptedOutput
    salt: bytes

    def __post_init__(self) -> None:
        if len(self.salt) != 32:
            raise ValueError("salt must be 32 bytes")

    def expected_digest(self) -> bytes:
        return compute_commit_digest(
            role=self.role,
            node=self.node,
            output_handle=self.output.ciphertext_handle,
            salt=self.salt,
        )

    def matches(self, commit: ExecutionCommit) -> bool:
        if commit.role is not self.role or commit.node != self.node:
            return False
        return commit.digest == self.expected_digest()
