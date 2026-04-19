// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.28;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {
    IExecutionCommitmentRegistry as IECR
} from "@blindference/contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {IBlindferenceAttestor} from "../interfaces/core/IBlindferenceAttestor.sol";

contract BlindferenceAttestor is TestnetCoreBase, IBlindferenceAttestor {
    /// @custom:storage-location erc7201:blindference.examples.BlindferenceAttestor
    struct Layout {
        IECR executionRegistry;
        mapping(uint256 invocationId => InferenceOutput) outputs;
    }

    bytes32 private constant _LAYOUT_SLOT = 0x348d74212429683a387dc95bd8244f0d90b47fbfcfd27055943b43cc2b540500;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_, address executionRegistry_) external initializer {
        require(executionRegistry_ != address(0), "ZeroAddress");
        __TestnetCoreBase_init(owner_);
        _layout().executionRegistry = IECR(executionRegistry_);
    }

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
    ) external nonReentrant {
        Layout storage l = _layout();
        if (l.outputs[invocationId].issuedAt != 0) {
            revert AlreadyCommitted();
        }
        if (validUntil <= block.timestamp) {
            revert InvalidValidity();
        }

        IECR.Invocation memory invocation = l.executionRegistry.invocation(invocationId);
        if (invocation.status != IECR.Status.VERIFIED) {
            revert InvocationNotVerified();
        }

        bytes32 expected = _outputDigest(
            responseHash,
            asset,
            recommendation,
            confidenceBps,
            priceAtIssue,
            validUntil,
            agent,
            modelKey
        );
        if (expected != invocation.executorOutput) {
            revert ResponseHashMismatch();
        }

        l.outputs[invocationId] = InferenceOutput({
            invocationId: invocationId,
            asset: asset,
            recommendation: recommendation,
            confidenceBps: confidenceBps,
            priceAtIssue: priceAtIssue,
            issuedAt: uint64(block.timestamp),
            validUntil: validUntil,
            agent: agent,
            responseHash: responseHash,
            modelKey: modelKey
        });

        emit InferenceOutputCommitted(
            invocationId,
            asset,
            recommendation,
            confidenceBps,
            priceAtIssue,
            validUntil,
            agent,
            responseHash,
            modelKey
        );
    }

    function outputOf(uint256 invocationId) external view returns (InferenceOutput memory) {
        InferenceOutput memory output = _layout().outputs[invocationId];
        if (output.issuedAt == 0) {
            revert UnknownOutput();
        }
        return output;
    }

    function outputDigest(
        bytes32 responseHash,
        bytes32 asset,
        Recommendation recommendation,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent,
        bytes32 modelKey
    ) external pure returns (bytes32) {
        return _outputDigest(responseHash, asset, recommendation, confidenceBps, priceAtIssue, validUntil, agent, modelKey);
    }

    function _outputDigest(
        bytes32 responseHash,
        bytes32 asset,
        Recommendation recommendation,
        uint16 confidenceBps,
        int256 priceAtIssue,
        uint64 validUntil,
        address agent,
        bytes32 modelKey
    ) private pure returns (bytes32) {
        return keccak256(
            abi.encode(responseHash, asset, recommendation, confidenceBps, priceAtIssue, validUntil, agent, modelKey)
        );
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly {
            l.slot := slot
        }
    }
}
