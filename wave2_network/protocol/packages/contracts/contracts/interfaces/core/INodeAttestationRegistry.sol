// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface INodeAttestationRegistry {
    struct Attestation {
        bytes32 attestationType;
        bytes32 documentHash;
        address counterparty;
        uint64 effectiveAt;
        uint64 expiresAt;
        bool revoked;
    }

    event AttestationCommitted(
        address indexed node,
        bytes32 indexed attestationType,
        address indexed counterparty,
        bytes32 documentHash,
        uint64 effectiveAt,
        uint64 expiresAt
    );

    event AttestationRevoked(address indexed node, bytes32 indexed attestationType, address indexed counterparty);

    error InvalidSignature();
    error InvalidWindow();
    error AttestationExpired();
    error AttestationNotFound();
    error NotNode();
    error CounterpartyConflict();

    function commit(
        address node,
        bytes32 attestationType,
        bytes32 documentHash,
        address counterparty,
        uint64 effectiveAt,
        uint64 expiresAt,
        bytes calldata signature
    ) external;

    function revoke(bytes32 attestationType, address counterparty) external;

    function hasValid(address node, bytes32 attestationType, address counterparty) external view returns (bool);

    function attestationOf(address node, bytes32 attestationType, address counterparty)
        external
        view
        returns (Attestation memory);

    function digest(
        address node,
        bytes32 attestationType,
        bytes32 documentHash,
        address counterparty,
        uint64 effectiveAt,
        uint64 expiresAt
    ) external view returns (bytes32);
}
