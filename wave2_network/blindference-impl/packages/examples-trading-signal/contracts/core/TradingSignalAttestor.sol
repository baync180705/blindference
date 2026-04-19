// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {
    IExecutionCommitmentRegistry as IECR
} from "@blindference/contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {ITradingSignalAttestor} from "../interfaces/core/ITradingSignalAttestor.sol";

contract TradingSignalAttestor is TestnetCoreBase, ITradingSignalAttestor {
    /// @custom:storage-location erc7201:blindference.examples.TradingSignalAttestor
    struct Layout {
        IECR executionRegistry;
        mapping(uint256 invocationId => Signal) signals;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xf3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f300;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_, address executionRegistry_) external initializer {
        require(executionRegistry_ != address(0), "ZeroAddress");
        __TestnetCoreBase_init(owner_);
        _layout().executionRegistry = IECR(executionRegistry_);
    }

    function commitSignal(
        uint256 invocationId,
        bytes32 asset,
        Direction direction,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent
    ) external nonReentrant {
        Layout storage l = _layout();
        if (l.signals[invocationId].issuedAt != 0) {
            revert AlreadyCommitted();
        }
        if (validUntil <= block.timestamp) {
            revert InvalidValidity();
        }

        IECR.Invocation memory inv = l.executionRegistry.invocation(invocationId);
        if (inv.status != IECR.Status.VERIFIED) {
            revert InvocationNotVerified();
        }

        bytes32 expected = _signalDigest(asset, direction, confidenceBps, priceAtIssue, validUntil, agent);
        if (expected != inv.executorOutput) {
            revert SignalHashMismatch();
        }

        l.signals[invocationId] = Signal({
            invocationId: invocationId,
            asset: asset,
            direction: direction,
            confidenceBps: confidenceBps,
            priceAtIssue: priceAtIssue,
            issuedAt: uint64(block.timestamp),
            validUntil: validUntil,
            agent: agent
        });

        emit SignalCommitted(invocationId, asset, direction, confidenceBps, priceAtIssue, validUntil, agent);
    }

    function signalOf(uint256 invocationId) external view returns (Signal memory) {
        Signal memory s = _layout().signals[invocationId];
        if (s.issuedAt == 0) {
            revert UnknownSignal();
        }
        return s;
    }

    function signalDigest(
        bytes32 asset,
        Direction direction,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent
    ) external pure returns (bytes32) {
        return _signalDigest(asset, direction, confidenceBps, priceAtIssue, validUntil, agent);
    }

    function _signalDigest(
        bytes32 asset,
        Direction direction,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent
    ) private pure returns (bytes32) {
        return keccak256(abi.encode(asset, direction, confidenceBps, priceAtIssue, validUntil, agent));
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly {
            l.slot := slot
        }
    }
}
