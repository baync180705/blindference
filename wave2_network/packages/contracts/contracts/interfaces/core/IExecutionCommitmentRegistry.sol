// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface IExecutionCommitmentRegistry {
    enum Role {
        EXECUTOR,
        CROSS_VERIFIER
    }

    enum Status {
        NONE,
        DISPATCHED,
        PARTIAL_COMMIT,
        BOTH_COMMITTED,
        PARTIAL_REVEAL,
        VERIFIED,
        ESCALATED
    }

    struct Invocation {
        uint256 escrowId;
        uint256 agentId;
        address executor;
        address crossVerifier;
        uint64 dispatchedAt;
        uint64 commitDeadline;
        uint64 revealDeadline;
        bytes32 executorCommit;
        bytes32 verifierCommit;
        bytes32 executorOutput;
        bytes32 verifierOutput;
        bool executorRevealed;
        bool verifierRevealed;
        Status status;
    }

    event Dispatched(
        uint256 indexed invocationId,
        uint256 indexed agentId,
        uint256 escrowId,
        address executor,
        address crossVerifier,
        uint64 commitDeadline,
        uint64 revealDeadline
    );
    event Committed(uint256 indexed invocationId, Role indexed role, address indexed node, bytes32 digest);
    event Revealed(uint256 indexed invocationId, Role indexed role, address indexed node, bytes32 outputHandle);
    event Verified(uint256 indexed invocationId, bytes32 outputHandle);
    event Escalated(uint256 indexed invocationId, string reason);

    error NotDispatcher();
    error AlreadyDispatched();
    error UnknownInvocation();
    error InvalidDeadlines();
    error SelfVoting();
    error ZeroAddress();
    error NotExpectedNode();
    error WrongStatus();
    error CommitDeadlinePassed();
    error RevealDeadlinePassed();
    error CommitDeadlineNotPassed();
    error RevealDeadlineNotPassed();
    error AlreadyCommitted();
    error AlreadyRevealed();
    error CommitMissing();
    error RevealMismatch();

    function dispatch(
        uint256 invocationId,
        uint256 escrowId,
        uint256 agentId,
        address executor,
        address crossVerifier,
        uint64 commitDeadline,
        uint64 revealDeadline
    ) external;

    function commit(uint256 invocationId, Role role, bytes32 digest) external;

    function reveal(uint256 invocationId, Role role, bytes32 outputHandle, bytes32 salt) external;

    function markCommitTimeout(uint256 invocationId) external;
    function markRevealTimeout(uint256 invocationId) external;

    function statusOf(uint256 invocationId) external view returns (Status);
    function verifiedOutput(uint256 invocationId) external view returns (bytes32);
    function invocation(uint256 invocationId) external view returns (Invocation memory);

    function commitDigest(Role role, address node, bytes32 outputHandle, bytes32 salt) external pure returns (bytes32);
}
