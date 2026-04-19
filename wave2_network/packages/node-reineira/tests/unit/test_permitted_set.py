from __future__ import annotations

import pytest

from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.shared_kernel.ids import NodeAddress


@pytest.mark.unit
def test_quorum_size_counts_leader_plus_verifiers() -> None:
    permitted = PermittedExecutorSet(
        leader=NodeAddress("0x1111111111111111111111111111111111111111"),
        verifiers=(
            NodeAddress("0x2222222222222222222222222222222222222222"),
            NodeAddress("0x3333333333333333333333333333333333333333"),
        ),
    )
    assert permitted.quorum_size == 3


@pytest.mark.unit
def test_includes_returns_true_for_members() -> None:
    leader = NodeAddress("0x1111111111111111111111111111111111111111")
    verifier = NodeAddress("0x2222222222222222222222222222222222222222")
    outsider = NodeAddress("0x9999999999999999999999999999999999999999")

    permitted = PermittedExecutorSet(leader=leader, verifiers=(verifier,))
    assert permitted.includes(leader)
    assert permitted.includes(verifier)
    assert not permitted.includes(outsider)


@pytest.mark.unit
def test_rejects_empty_verifier_set() -> None:
    with pytest.raises(ValueError, match="At least one verifier"):
        PermittedExecutorSet(
            leader=NodeAddress("0x1111111111111111111111111111111111111111"),
            verifiers=(),
        )


@pytest.mark.unit
def test_rejects_duplicate_node() -> None:
    leader = NodeAddress("0x1111111111111111111111111111111111111111")
    with pytest.raises(ValueError, match="distinct"):
        PermittedExecutorSet(leader=leader, verifiers=(leader,))
