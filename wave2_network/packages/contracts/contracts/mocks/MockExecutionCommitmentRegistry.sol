// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IExecutionCommitmentRegistry} from "../interfaces/core/IExecutionCommitmentRegistry.sol";

contract MockExecutionCommitmentRegistry is IExecutionCommitmentRegistry {
    mapping(uint256 invocationId => Invocation) private _invocations;

    function setInvocation(
        uint256 invocationId,
        uint256 escrowId,
        uint256 agentId,
        address executor,
        address crossVerifier,
        Status status
    ) external {
        Invocation storage inv = _invocations[invocationId];
        inv.escrowId = escrowId;
        inv.agentId = agentId;
        inv.executor = executor;
        inv.crossVerifier = crossVerifier;
        inv.status = status;
    }

    function invocation(uint256 invocationId) external view returns (Invocation memory) {
        return _invocations[invocationId];
    }

    function statusOf(uint256 invocationId) external view returns (Status) {
        return _invocations[invocationId].status;
    }

    function verifiedOutput(uint256 invocationId) external view returns (bytes32) {
        Invocation storage inv = _invocations[invocationId];
        return inv.status == Status.VERIFIED ? inv.executorOutput : bytes32(0);
    }

    function dispatch(uint256, uint256, uint256, address, address, uint64, uint64) external pure {
        revert("mock");
    }

    function commit(uint256, Role, bytes32) external pure {
        revert("mock");
    }

    function reveal(uint256, Role, bytes32, bytes32) external pure {
        revert("mock");
    }

    function markCommitTimeout(uint256) external pure {
        revert("mock");
    }

    function markRevealTimeout(uint256) external pure {
        revert("mock");
    }

    function commitDigest(Role, address, bytes32, bytes32) external pure returns (bytes32) {
        return bytes32(0);
    }
}
