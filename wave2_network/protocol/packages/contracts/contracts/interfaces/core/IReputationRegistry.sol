// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface IReputationRegistry {
    enum FraudReason {
        ARBITER_MINORITY,
        EXECUTOR_WRONG,
        VERIFIER_WRONG,
        ARBITER_NO_REVEAL,
        EXECUTOR_NO_REVEAL,
        VERIFIER_NO_REVEAL
    }

    struct Reputation {
        uint64 score;
        uint64 cycleResetAt;
        uint64 cyclesActive;
        uint64 cyclesGuilty;
    }

    event HonestCycleRecorded(address indexed node, uint64 cycleEpoch, uint64 newScore);
    event FraudRecorded(address indexed node, uint256 indexed invocationId, FraudReason reason);

    error AlreadyResetThisCycle();
    error AlreadyCreditedThisCycle();
    error CycleNotEnded();
    error NoArbitrationMajority();
    error NodeNotOnLosingSide();
    error UnknownNode();
    error InvalidCycle();

    function recordFraudFromArbitration(uint256 invocationId, address node, FraudReason reason) external;
    function recordHonestCycle(address node, uint64 cycleEpoch) external;

    function reputationOf(address node) external view returns (Reputation memory);
    function arbitrationFrequencyBps(address node) external view returns (uint16);
    function isGuiltyInCycle(address node, uint64 cycleEpoch) external view returns (bool);
    function currentCycle() external view returns (uint64);
}
