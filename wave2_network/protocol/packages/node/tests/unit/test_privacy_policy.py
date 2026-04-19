from __future__ import annotations

from dataclasses import replace

import pytest

from blindference_node.domain.privacy.eligibility import ExecutorEligibility
from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.privacy.policy import PolicyViolation, PrivacyPolicy
from blindference_node.domain.shared_kernel.ids import NodeAddress
from blindference_node.infrastructure.attestations import InMemoryNodeAttestationProvider


@pytest.mark.unit
def test_accepts_eligible_node(
    eligibility_set: list[ExecutorEligibility], privacy_policy: PrivacyPolicy
) -> None:
    assert all(privacy_policy.accepts(e) for e in eligibility_set)


@pytest.mark.unit
def test_rejects_under_minimum_stake(
    eligibility_set: list[ExecutorEligibility], privacy_policy: PrivacyPolicy
) -> None:
    weak = replace(eligibility_set[0], slashing_stake_wei=10)
    assert not privacy_policy.accepts(weak)


@pytest.mark.unit
def test_rejects_missing_zdr_when_required(
    eligibility_set: list[ExecutorEligibility], privacy_policy: PrivacyPolicy
) -> None:
    no_zdr = replace(eligibility_set[0], zdr_attested=False)
    assert not privacy_policy.accepts(no_zdr)


@pytest.mark.unit
def test_rejects_jurisdiction_outside_allowlist(
    eligibility_set: list[ExecutorEligibility], privacy_policy: PrivacyPolicy
) -> None:
    other = replace(eligibility_set[0], jurisdiction="cn-north-1")
    assert not privacy_policy.accepts(other)


@pytest.mark.unit
def test_rejects_when_capability_missing(
    eligibility_set: list[ExecutorEligibility], privacy_policy: PrivacyPolicy
) -> None:
    no_cap = replace(eligibility_set[0], capabilities=frozenset())
    assert not privacy_policy.accepts(no_cap)


@pytest.mark.unit
def test_assert_set_compliant_passes_for_valid_set(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
    attestations: InMemoryNodeAttestationProvider,
) -> None:
    elig_map = {e.node: e for e in eligibility_set}
    privacy_policy.assert_set_compliant(permitted, elig_map, attestations)


@pytest.mark.unit
def test_assert_set_compliant_rejects_unknown_node(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
) -> None:
    elig_map = {e.node: e for e in eligibility_set}
    elig_map.pop(permitted.leader)
    with pytest.raises(PolicyViolation, match="No eligibility profile"):
        privacy_policy.assert_set_compliant(permitted, elig_map)


@pytest.mark.unit
def test_assert_set_compliant_rejects_below_min_quorum(
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
) -> None:
    leader = NodeAddress("0x1111111111111111111111111111111111111111")
    one_verifier = NodeAddress("0x2222222222222222222222222222222222222222")
    small_set = PermittedExecutorSet(leader=leader, verifiers=(one_verifier,))

    elig_map = {e.node: e for e in eligibility_set}
    with pytest.raises(PolicyViolation, match="Quorum size"):
        privacy_policy.assert_set_compliant(small_set, elig_map)


@pytest.mark.unit
def test_assert_set_compliant_passes_when_no_attestations_required_and_none_supplied(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
) -> None:
    elig_map = {e.node: e for e in eligibility_set}
    privacy_policy.assert_set_compliant(permitted, elig_map)


@pytest.mark.unit
def test_assert_set_compliant_requires_provider_when_attestations_required(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
    attestation_zdr: bytes,
) -> None:
    strict_policy = replace(privacy_policy, required_attestations=frozenset({attestation_zdr}))
    elig_map = {e.node: e for e in eligibility_set}
    with pytest.raises(PolicyViolation, match="no NodeAttestationProvider"):
        strict_policy.assert_set_compliant(permitted, elig_map)


@pytest.mark.unit
def test_assert_set_compliant_passes_when_all_nodes_attested(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
    attestations: InMemoryNodeAttestationProvider,
    attestation_zdr: bytes,
) -> None:
    strict_policy = replace(privacy_policy, required_attestations=frozenset({attestation_zdr}))
    elig_map = {e.node: e for e in eligibility_set}
    strict_policy.assert_set_compliant(permitted, elig_map, attestations)


@pytest.mark.unit
def test_assert_set_compliant_rejects_when_a_node_lacks_required_attestation(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
    attestations: InMemoryNodeAttestationProvider,
    attestation_zdr: bytes,
) -> None:
    strict_policy = replace(privacy_policy, required_attestations=frozenset({attestation_zdr}))
    attestations.revoke(node=permitted.verifiers[0], attestation_type=attestation_zdr)

    elig_map = {e.node: e for e in eligibility_set}
    with pytest.raises(PolicyViolation, match="missing attestation"):
        strict_policy.assert_set_compliant(permitted, elig_map, attestations)


@pytest.mark.unit
def test_bilateral_attestation_required_for_specific_counterparty(
    permitted: PermittedExecutorSet,
    eligibility_set: list[ExecutorEligibility],
    privacy_policy: PrivacyPolicy,
    attestations: InMemoryNodeAttestationProvider,
    attestation_hipaa: bytes,
) -> None:
    counterparty = NodeAddress("0xcccccccccccccccccccccccccccccccccccccccc")

    strict_policy = replace(
        privacy_policy,
        required_attestations=frozenset({attestation_hipaa}),
        bilateral_counterparty=counterparty,
    )

    elig_map = {e.node: e for e in eligibility_set}

    with pytest.raises(PolicyViolation, match="missing attestation"):
        strict_policy.assert_set_compliant(permitted, elig_map, attestations)

    for node in permitted.all():
        attestations.grant(node=node, attestation_type=attestation_hipaa, counterparty=counterparty)
    strict_policy.assert_set_compliant(permitted, elig_map, attestations)
