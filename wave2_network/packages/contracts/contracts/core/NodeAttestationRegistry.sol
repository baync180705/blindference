// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {INodeAttestationRegistry} from "../interfaces/core/INodeAttestationRegistry.sol";

contract NodeAttestationRegistry is TestnetCoreBase, INodeAttestationRegistry {
    using MessageHashUtils for bytes32;

    /// @custom:storage-location erc7201:blindference.NodeAttestationRegistry
    struct Layout {
        mapping(bytes32 key => Attestation) attestations;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xb1f5a8c6e0d2f4b6a8c0e2d4f6a8c0e2d4f6a8c0e2d4f6a8c0e2d4f6a8c0ee00;

    bytes32 private constant _DOMAIN_TAG = keccak256("blindference.node-attestation.v1");

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_) external initializer {
        __TestnetCoreBase_init(owner_);
    }

    function commit(
        address node,
        bytes32 attestationType,
        bytes32 documentHash,
        address counterparty,
        uint64 effectiveAt,
        uint64 expiresAt,
        bytes calldata signature
    ) external nonReentrant {
        if (effectiveAt == 0) {
            revert InvalidWindow();
        }
        if (expiresAt != 0 && expiresAt <= effectiveAt) {
            revert InvalidWindow();
        }
        if (expiresAt != 0 && expiresAt <= block.timestamp) {
            revert AttestationExpired();
        }

        bytes32 d = _digest(node, attestationType, documentHash, counterparty, effectiveAt, expiresAt);
        address recovered = ECDSA.recover(d.toEthSignedMessageHash(), signature);
        if (recovered != node) {
            revert InvalidSignature();
        }

        bytes32 key = _key(node, attestationType, counterparty);
        _layout().attestations[key] = Attestation({
            attestationType: attestationType,
            documentHash: documentHash,
            counterparty: counterparty,
            effectiveAt: effectiveAt,
            expiresAt: expiresAt,
            revoked: false
        });

        emit AttestationCommitted(node, attestationType, counterparty, documentHash, effectiveAt, expiresAt);
    }

    function revoke(bytes32 attestationType, address counterparty) external nonReentrant {
        address node = _msgSender();
        bytes32 key = _key(node, attestationType, counterparty);
        Attestation storage a = _layout().attestations[key];
        if (a.effectiveAt == 0) {
            revert AttestationNotFound();
        }
        a.revoked = true;
        emit AttestationRevoked(node, attestationType, counterparty);
    }

    function hasValid(address node, bytes32 attestationType, address counterparty) external view returns (bool) {
        Attestation storage a = _layout().attestations[_key(node, attestationType, counterparty)];
        return _isValid(a);
    }

    function attestationOf(address node, bytes32 attestationType, address counterparty)
        external
        view
        returns (Attestation memory)
    {
        return _layout().attestations[_key(node, attestationType, counterparty)];
    }

    function digest(
        address node,
        bytes32 attestationType,
        bytes32 documentHash,
        address counterparty,
        uint64 effectiveAt,
        uint64 expiresAt
    ) external view returns (bytes32) {
        return _digest(node, attestationType, documentHash, counterparty, effectiveAt, expiresAt);
    }

    function _digest(
        address node,
        bytes32 attestationType,
        bytes32 documentHash,
        address counterparty,
        uint64 effectiveAt,
        uint64 expiresAt
    ) private view returns (bytes32) {
        return keccak256(
            abi.encode(
                _DOMAIN_TAG,
                block.chainid,
                address(this),
                node,
                attestationType,
                documentHash,
                counterparty,
                effectiveAt,
                expiresAt
            )
        );
    }

    function _key(address node, bytes32 attestationType, address counterparty) private pure returns (bytes32) {
        return keccak256(abi.encode(node, attestationType, counterparty));
    }

    function _isValid(Attestation storage a) private view returns (bool) {
        if (a.effectiveAt == 0) {
            return false;
        }
        if (a.revoked) {
            return false;
        }
        if (block.timestamp < a.effectiveAt) {
            return false;
        }
        if (a.expiresAt != 0 && block.timestamp >= a.expiresAt) {
            return false;
        }
        return true;
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
