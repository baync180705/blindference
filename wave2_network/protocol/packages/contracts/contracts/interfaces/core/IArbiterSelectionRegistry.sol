// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface IArbiterSelectionRegistry {
    enum ArbitrationStatus {
        NONE,
        SELECTED,
        COMMITTING,
        REVEALING,
        RESOLVED_MAJORITY,
        TIMED_OUT
    }

    struct Arbitration {
        uint256 invocationId;
        address[] arbiters;
        uint64 selectedAt;
        uint64 commitDeadline;
        uint64 revealDeadline;
        bytes32 majorityOutput;
        uint8 majorityCount;
        ArbitrationStatus status;
    }

    event ArbiterRegistered(address indexed arbiter, uint256 stake);
    event ArbiterUnregistered(address indexed arbiter, uint256 returnedStake);
    event ArbitersSelected(uint256 indexed invocationId, address[] arbiters);
    event ArbiterCommitted(uint256 indexed invocationId, address indexed arbiter, bytes32 digest);
    event ArbiterRevealed(uint256 indexed invocationId, address indexed arbiter, bytes32 outputHandle);
    event ArbitrationResolved(uint256 indexed invocationId, bytes32 majorityOutput, uint8 majorityCount);
    event ArbitrationTimedOut(uint256 indexed invocationId);

    error InsufficientStake();
    error AlreadyRegistered();
    error NotRegistered();
    error PoolTooSmall();
    error AlreadyArbitrating();
    error UnknownInvocation();
    error InvocationNotEscalated();
    error NotAnArbiter();
    error WrongStatus();
    error AlreadyCommitted();
    error AlreadyRevealed();
    error CommitDeadlinePassed();
    error RevealDeadlinePassed();
    error CommitDeadlineNotPassed();
    error RevealDeadlineNotPassed();
    error RevealMismatch();
    error CommitMissing();
    error InvalidK();
    error CooldownActive(address arbiter);

    function registerArbiter() external payable;
    function unregisterArbiter() external;

    function requestArbitration(uint256 invocationId, uint8 k) external returns (address[] memory);

    function arbiterCommit(uint256 invocationId, bytes32 digest) external;
    function arbiterReveal(uint256 invocationId, bytes32 outputHandle, bytes32 salt) external;

    function finalize(uint256 invocationId) external;

    function arbitrationOf(uint256 invocationId) external view returns (Arbitration memory);
    function commitDigest(address arbiter, bytes32 outputHandle, bytes32 salt) external pure returns (bytes32);
    function commitOf(uint256 invocationId, address arbiter) external view returns (bytes32);
    function revealOf(uint256 invocationId, address arbiter) external view returns (bytes32);
    function isRegistered(address arbiter) external view returns (bool);
    function poolSize() external view returns (uint256);
}
