// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

interface IBlindferenceAttestor {
    enum Recommendation {
        SELL,
        HOLD,
        BUY
    }

    struct InferenceOutput {
        uint256 invocationId;
        bytes32 asset;
        Recommendation recommendation;
        uint16 confidenceBps;
        int256 priceAtIssue;
        uint64 issuedAt;
        uint64 validUntil;
        address agent;
        bytes32 responseHash;
        bytes32 modelKey;
    }

    event InferenceOutputCommitted(
        uint256 indexed invocationId,
        bytes32 indexed asset,
        Recommendation indexed recommendation,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent,
        bytes32 responseHash,
        bytes32 modelKey
    );

    error AlreadyCommitted();
    error InvalidValidity();
    error InvocationNotVerified();
    error ResponseHashMismatch();
    error UnknownOutput();

    function commitInferenceOutput(
        uint256 invocationId,
        bytes32 asset,
        Recommendation recommendation,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent,
        bytes32 responseHash,
        bytes32 modelKey
    ) external;

    function outputOf(uint256 invocationId) external view returns (InferenceOutput memory);

    function outputDigest(
        bytes32 responseHash,
        bytes32 asset,
        Recommendation recommendation,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent,
        bytes32 modelKey
    ) external pure returns (bytes32);
}
