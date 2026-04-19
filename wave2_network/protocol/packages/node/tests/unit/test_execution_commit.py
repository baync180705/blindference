from __future__ import annotations

import pytest

from blindference_node.domain.inference.commit import (
    ExecutionCommit,
    ExecutionReveal,
    ExecutionRole,
)
from blindference_node.domain.inference.encrypted_output import EncryptedOutput
from blindference_node.domain.shared_kernel.ids import NodeAddress


def _reveal(
    role: ExecutionRole,
    node: NodeAddress,
    output: EncryptedOutput,
    salt: bytes = b"\x01" * 32,
) -> ExecutionReveal:
    return ExecutionReveal(role=role, node=node, output=output, salt=salt)


@pytest.mark.unit
def test_reveal_matches_commit_built_from_same_inputs(
    leader: NodeAddress, encrypted_output: EncryptedOutput
) -> None:
    reveal = _reveal(ExecutionRole.EXECUTOR, leader, encrypted_output)
    commit = ExecutionCommit(
        role=ExecutionRole.EXECUTOR, node=leader, digest=reveal.expected_digest()
    )
    assert reveal.matches(commit) is True


@pytest.mark.unit
def test_reveal_does_not_match_when_salt_differs(
    leader: NodeAddress, encrypted_output: EncryptedOutput
) -> None:
    reveal = _reveal(ExecutionRole.EXECUTOR, leader, encrypted_output, salt=b"\x01" * 32)
    other_reveal = _reveal(ExecutionRole.EXECUTOR, leader, encrypted_output, salt=b"\x02" * 32)
    commit = ExecutionCommit(
        role=ExecutionRole.EXECUTOR, node=leader, digest=other_reveal.expected_digest()
    )
    assert reveal.matches(commit) is False


@pytest.mark.unit
def test_reveal_does_not_match_commit_with_different_role(
    leader: NodeAddress, encrypted_output: EncryptedOutput
) -> None:
    reveal = _reveal(ExecutionRole.EXECUTOR, leader, encrypted_output)
    commit = ExecutionCommit(
        role=ExecutionRole.CROSS_VERIFIER, node=leader, digest=reveal.expected_digest()
    )
    assert reveal.matches(commit) is False


@pytest.mark.unit
def test_reveal_does_not_match_commit_with_different_node(
    leader: NodeAddress,
    verifiers: tuple[NodeAddress, ...],
    encrypted_output: EncryptedOutput,
) -> None:
    reveal = _reveal(ExecutionRole.EXECUTOR, leader, encrypted_output)
    commit = ExecutionCommit(
        role=ExecutionRole.EXECUTOR, node=verifiers[0], digest=reveal.expected_digest()
    )
    assert reveal.matches(commit) is False


@pytest.mark.unit
def test_commit_rejects_wrong_digest_length(leader: NodeAddress) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        ExecutionCommit(role=ExecutionRole.EXECUTOR, node=leader, digest=b"\x00" * 31)


@pytest.mark.unit
def test_reveal_rejects_wrong_salt_length(
    leader: NodeAddress, encrypted_output: EncryptedOutput
) -> None:
    with pytest.raises(ValueError, match="salt must be 32 bytes"):
        ExecutionReveal(
            role=ExecutionRole.EXECUTOR, node=leader, output=encrypted_output, salt=b"\x00" * 16
        )
