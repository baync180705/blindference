from __future__ import annotations

from datetime import datetime

import pytest

from blindference_node.domain.inference.commit import (
    CommitMismatch,
    ExecutionCommit,
    ExecutionReveal,
    ExecutionRole,
)
from blindference_node.domain.inference.encrypted_output import EncryptedOutput
from blindference_node.domain.inference.events import (
    InferenceJobAttested,
    InferenceJobDispatched,
    InferenceJobExecuted,
    InferenceJobFinalized,
    InferenceJobOpened,
    InferenceJobVerified,
)
from blindference_node.domain.inference.inference_job import (
    IllegalTransition,
    InferenceJob,
    InferenceJobState,
)
from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.shared_kernel.ids import (
    AgentId,
    EscrowId,
    InvocationId,
    NodeAddress,
)


def _open(
    *,
    invocation_id: InvocationId,
    agent_id: AgentId,
    escrow_id: EscrowId,
    permitted: PermittedExecutorSet,
    now: datetime,
) -> InferenceJob:
    return InferenceJob.open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        opened_at=now,
    )


def _reveals(
    executor: NodeAddress,
    cross_verifier: NodeAddress,
    output: EncryptedOutput,
) -> tuple[ExecutionReveal, ExecutionReveal]:
    e_reveal = ExecutionReveal(
        role=ExecutionRole.EXECUTOR,
        node=executor,
        output=output,
        salt=b"\x11" * 32,
    )
    v_reveal = ExecutionReveal(
        role=ExecutionRole.CROSS_VERIFIER,
        node=cross_verifier,
        output=output,
        salt=b"\x22" * 32,
    )
    return e_reveal, v_reveal


def _commits(
    e_reveal: ExecutionReveal, v_reveal: ExecutionReveal
) -> tuple[ExecutionCommit, ExecutionCommit]:
    return (
        ExecutionCommit(
            role=ExecutionRole.EXECUTOR,
            node=e_reveal.node,
            digest=e_reveal.expected_digest(),
        ),
        ExecutionCommit(
            role=ExecutionRole.CROSS_VERIFIER,
            node=v_reveal.node,
            digest=v_reveal.expected_digest(),
        ),
    )


@pytest.mark.unit
def test_open_starts_in_requested(invocation_id, agent_id, escrow_id, permitted, now) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    assert job.state is InferenceJobState.REQUESTED
    events = job.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], InferenceJobOpened)


@pytest.mark.unit
def test_full_happy_path_walks_lifecycle(
    invocation_id,
    agent_id,
    escrow_id,
    permitted,
    encrypted_input,
    encrypted_output,
    now,
) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    job.pull_events()

    executor = permitted.leader
    cross_verifier = permitted.verifiers[0]

    job.dispatch(
        executor=executor,
        cross_verifier=cross_verifier,
        encrypted_input=encrypted_input,
        at=now,
    )
    assert job.state is InferenceJobState.DISPATCHED
    assert isinstance(job.pull_events()[0], InferenceJobDispatched)

    e_reveal, v_reveal = _reveals(executor, cross_verifier, encrypted_output)
    e_commit, v_commit = _commits(e_reveal, v_reveal)

    job.record_commits(executor_commit=e_commit, verifier_commit=v_commit, at=now)
    assert job.state is InferenceJobState.EXECUTED
    assert isinstance(job.pull_events()[0], InferenceJobExecuted)

    job.verify_reveals(executor_reveal=e_reveal, verifier_reveal=v_reveal, at=now)
    assert job.state is InferenceJobState.VERIFIED
    assert job.verified_output == encrypted_output
    assert isinstance(job.pull_events()[0], InferenceJobVerified)

    digest = job.attest(at=now)
    assert job.state is InferenceJobState.ATTESTED
    assert job.attestation_digest == digest
    assert len(digest) == 32
    assert isinstance(job.pull_events()[0], InferenceJobAttested)

    receipt = b"\xde" * 32
    job.finalize(on_chain_receipt_hash=receipt, at=now)
    assert job.state is InferenceJobState.FINALIZED
    assert job.on_chain_receipt_hash == receipt
    assert isinstance(job.pull_events()[0], InferenceJobFinalized)


@pytest.mark.unit
def test_dispatch_rejects_self_voting(
    invocation_id, agent_id, escrow_id, permitted, encrypted_input, now
) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    with pytest.raises(IllegalTransition, match="no self-voting"):
        job.dispatch(
            executor=permitted.leader,
            cross_verifier=permitted.leader,
            encrypted_input=encrypted_input,
            at=now,
        )


@pytest.mark.unit
def test_dispatch_rejects_executor_outside_permitted(
    invocation_id, agent_id, escrow_id, permitted, encrypted_input, now
) -> None:
    outsider = NodeAddress("0xdeadbeef00000000000000000000000000000000")
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    with pytest.raises(IllegalTransition, match="not in permitted"):
        job.dispatch(
            executor=outsider,
            cross_verifier=permitted.verifiers[0],
            encrypted_input=encrypted_input,
            at=now,
        )


@pytest.mark.unit
def test_record_commits_rejects_swapped_roles(
    invocation_id,
    agent_id,
    escrow_id,
    permitted,
    encrypted_input,
    encrypted_output,
    now,
) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    job.dispatch(
        executor=permitted.leader,
        cross_verifier=permitted.verifiers[0],
        encrypted_input=encrypted_input,
        at=now,
    )

    e_reveal, v_reveal = _reveals(permitted.leader, permitted.verifiers[0], encrypted_output)
    e_commit_wrong_role = ExecutionCommit(
        role=ExecutionRole.CROSS_VERIFIER,
        node=permitted.leader,
        digest=e_reveal.expected_digest(),
    )
    v_commit = ExecutionCommit(
        role=ExecutionRole.CROSS_VERIFIER,
        node=permitted.verifiers[0],
        digest=v_reveal.expected_digest(),
    )

    with pytest.raises(IllegalTransition, match="role EXECUTOR"):
        job.record_commits(executor_commit=e_commit_wrong_role, verifier_commit=v_commit, at=now)


@pytest.mark.unit
def test_verify_reveals_rejects_mismatched_outputs(
    invocation_id, agent_id, escrow_id, permitted, encrypted_input, now
) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    job.dispatch(
        executor=permitted.leader,
        cross_verifier=permitted.verifiers[0],
        encrypted_input=encrypted_input,
        at=now,
    )

    out_a = EncryptedOutput(ciphertext_handle=b"\xaa" * 32, model_version=7, metadata={})
    out_b = EncryptedOutput(ciphertext_handle=b"\xbb" * 32, model_version=7, metadata={})

    e_reveal = ExecutionReveal(
        role=ExecutionRole.EXECUTOR,
        node=permitted.leader,
        output=out_a,
        salt=b"\x11" * 32,
    )
    v_reveal = ExecutionReveal(
        role=ExecutionRole.CROSS_VERIFIER,
        node=permitted.verifiers[0],
        output=out_b,
        salt=b"\x22" * 32,
    )
    e_commit = ExecutionCommit(
        role=ExecutionRole.EXECUTOR,
        node=permitted.leader,
        digest=e_reveal.expected_digest(),
    )
    v_commit = ExecutionCommit(
        role=ExecutionRole.CROSS_VERIFIER,
        node=permitted.verifiers[0],
        digest=v_reveal.expected_digest(),
    )

    job.record_commits(executor_commit=e_commit, verifier_commit=v_commit, at=now)

    with pytest.raises(CommitMismatch, match="different outputs"):
        job.verify_reveals(executor_reveal=e_reveal, verifier_reveal=v_reveal, at=now)


@pytest.mark.unit
def test_verify_reveals_rejects_forged_reveal(
    invocation_id,
    agent_id,
    escrow_id,
    permitted,
    encrypted_input,
    encrypted_output,
    now,
) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    job.dispatch(
        executor=permitted.leader,
        cross_verifier=permitted.verifiers[0],
        encrypted_input=encrypted_input,
        at=now,
    )

    e_reveal, v_reveal = _reveals(permitted.leader, permitted.verifiers[0], encrypted_output)
    e_commit, v_commit = _commits(e_reveal, v_reveal)
    job.record_commits(executor_commit=e_commit, verifier_commit=v_commit, at=now)

    forged_reveal = ExecutionReveal(
        role=ExecutionRole.EXECUTOR,
        node=permitted.leader,
        output=encrypted_output,
        salt=b"\xff" * 32,
    )

    with pytest.raises(CommitMismatch, match="executor reveal does not match"):
        job.verify_reveals(executor_reveal=forged_reveal, verifier_reveal=v_reveal, at=now)


@pytest.mark.unit
def test_cannot_skip_states(invocation_id, agent_id, escrow_id, permitted, now) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    with pytest.raises(IllegalTransition):
        job.attest(at=now)


@pytest.mark.unit
def test_finalize_rejects_wrong_receipt_size(
    invocation_id,
    agent_id,
    escrow_id,
    permitted,
    encrypted_input,
    encrypted_output,
    now,
) -> None:
    job = _open(
        invocation_id=invocation_id,
        agent_id=agent_id,
        escrow_id=escrow_id,
        permitted=permitted,
        now=now,
    )
    job.dispatch(
        executor=permitted.leader,
        cross_verifier=permitted.verifiers[0],
        encrypted_input=encrypted_input,
        at=now,
    )
    e_reveal, v_reveal = _reveals(permitted.leader, permitted.verifiers[0], encrypted_output)
    e_commit, v_commit = _commits(e_reveal, v_reveal)
    job.record_commits(executor_commit=e_commit, verifier_commit=v_commit, at=now)
    job.verify_reveals(executor_reveal=e_reveal, verifier_reveal=v_reveal, at=now)
    job.attest(at=now)

    with pytest.raises(IllegalTransition, match="32 bytes"):
        job.finalize(on_chain_receipt_hash=b"\x00" * 16, at=now)
