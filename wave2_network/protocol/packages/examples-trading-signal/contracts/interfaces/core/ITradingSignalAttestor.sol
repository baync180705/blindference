// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface ITradingSignalAttestor {
    enum Direction {
        SELL,
        HOLD,
        BUY
    }

    struct Signal {
        uint256 invocationId;
        bytes32 asset;
        Direction direction;
        uint16 confidenceBps;
        int256 priceAtIssue;
        uint64 issuedAt;
        uint64 validUntil;
        address agent;
    }

    event SignalCommitted(
        uint256 indexed invocationId,
        bytes32 indexed asset,
        Direction indexed direction,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent
    );

    error InvocationNotVerified();
    error SignalHashMismatch();
    error AlreadyCommitted();
    error InvalidValidity();
    error UnknownSignal();

    /// @notice Encodes signal payload identical to the bytes32 the Blindference
    ///         executor + cross-verifier committed to via `ExecutionCommitmentRegistry`.
    function signalDigest(
        bytes32 asset,
        Direction direction,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent
    ) external pure returns (bytes32);

    function commitSignal(
        uint256 invocationId,
        bytes32 asset,
        Direction direction,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent
    ) external;

    function signalOf(uint256 invocationId) external view returns (Signal memory);
}
