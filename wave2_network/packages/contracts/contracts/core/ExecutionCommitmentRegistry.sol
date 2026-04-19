// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IExecutionCommitmentRegistry} from "../interfaces/core/IExecutionCommitmentRegistry.sol";

contract ExecutionCommitmentRegistry is TestnetCoreBase, IExecutionCommitmentRegistry {
    /// @custom:storage-location erc7201:blindference.ExecutionCommitmentRegistry
    struct Layout {
        address dispatcher;
        mapping(uint256 invocationId => Invocation) invocations;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xc7e4d8a3f5b9e1c0d2f4b6a8c0e2d4f6a8c0e2d4f6a8c0e2d4f6a8c0e2c0fc00;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_, address dispatcher_) external initializer {
        if (dispatcher_ == address(0)) {
            revert ZeroAddress();
        }
        __TestnetCoreBase_init(owner_);
        _layout().dispatcher = dispatcher_;
    }

    function setDispatcher(address dispatcher_) external onlyOwner {
        if (dispatcher_ == address(0)) {
            revert ZeroAddress();
        }
        _layout().dispatcher = dispatcher_;
    }

    function dispatcher() external view returns (address) {
        return _layout().dispatcher;
    }

    function dispatch(
        uint256 invocationId,
        uint256 escrowId,
        uint256 agentId,
        address executor,
        address crossVerifier,
        uint64 commitDeadline,
        uint64 revealDeadline
    ) external nonReentrant {
        Layout storage l = _layout();
        if (_msgSender() != l.dispatcher) {
            revert NotDispatcher();
        }
        if (executor == address(0) || crossVerifier == address(0)) {
            revert ZeroAddress();
        }
        if (executor == crossVerifier) {
            revert SelfVoting();
        }
        if (commitDeadline <= block.timestamp) {
            revert InvalidDeadlines();
        }
        if (revealDeadline <= commitDeadline) {
            revert InvalidDeadlines();
        }

        Invocation storage inv = l.invocations[invocationId];
        if (inv.status != Status.NONE) {
            revert AlreadyDispatched();
        }

        inv.escrowId = escrowId;
        inv.agentId = agentId;
        inv.executor = executor;
        inv.crossVerifier = crossVerifier;
        inv.dispatchedAt = uint64(block.timestamp);
        inv.commitDeadline = commitDeadline;
        inv.revealDeadline = revealDeadline;
        inv.status = Status.DISPATCHED;

        emit Dispatched(invocationId, agentId, escrowId, executor, crossVerifier, commitDeadline, revealDeadline);
    }

    function commit(uint256 invocationId, Role role, bytes32 digest) external nonReentrant {
        Layout storage l = _layout();
        Invocation storage inv = l.invocations[invocationId];
        if (inv.status == Status.NONE) {
            revert UnknownInvocation();
        }
        if (inv.status != Status.DISPATCHED && inv.status != Status.PARTIAL_COMMIT) {
            revert WrongStatus();
        }
        if (block.timestamp >= inv.commitDeadline) {
            revert CommitDeadlinePassed();
        }

        address sender = _msgSender();
        if (role == Role.EXECUTOR) {
            if (sender != inv.executor) {
                revert NotExpectedNode();
            }
            if (inv.executorCommit != bytes32(0)) {
                revert AlreadyCommitted();
            }
            inv.executorCommit = digest;
        } else {
            if (sender != inv.crossVerifier) {
                revert NotExpectedNode();
            }
            if (inv.verifierCommit != bytes32(0)) {
                revert AlreadyCommitted();
            }
            inv.verifierCommit = digest;
        }

        if (inv.executorCommit != bytes32(0) && inv.verifierCommit != bytes32(0)) {
            inv.status = Status.BOTH_COMMITTED;
        } else {
            inv.status = Status.PARTIAL_COMMIT;
        }

        emit Committed(invocationId, role, sender, digest);
    }

    function reveal(uint256 invocationId, Role role, bytes32 outputHandle, bytes32 salt) external nonReentrant {
        Layout storage l = _layout();
        Invocation storage inv = l.invocations[invocationId];
        if (inv.status == Status.NONE) {
            revert UnknownInvocation();
        }
        if (inv.status != Status.BOTH_COMMITTED && inv.status != Status.PARTIAL_REVEAL) {
            revert WrongStatus();
        }
        if (block.timestamp >= inv.revealDeadline) {
            revert RevealDeadlinePassed();
        }

        address sender = _msgSender();
        bytes32 priorCommit;
        if (role == Role.EXECUTOR) {
            if (sender != inv.executor) {
                revert NotExpectedNode();
            }
            if (inv.executorRevealed) {
                revert AlreadyRevealed();
            }
            priorCommit = inv.executorCommit;
        } else {
            if (sender != inv.crossVerifier) {
                revert NotExpectedNode();
            }
            if (inv.verifierRevealed) {
                revert AlreadyRevealed();
            }
            priorCommit = inv.verifierCommit;
        }
        if (priorCommit == bytes32(0)) {
            revert CommitMissing();
        }

        bytes32 expected = _commitDigest(role, sender, outputHandle, salt);
        if (expected != priorCommit) {
            revert RevealMismatch();
        }

        if (role == Role.EXECUTOR) {
            inv.executorOutput = outputHandle;
            inv.executorRevealed = true;
        } else {
            inv.verifierOutput = outputHandle;
            inv.verifierRevealed = true;
        }

        emit Revealed(invocationId, role, sender, outputHandle);

        if (inv.executorRevealed && inv.verifierRevealed) {
            if (inv.executorOutput == inv.verifierOutput) {
                inv.status = Status.VERIFIED;
                emit Verified(invocationId, inv.executorOutput);
            } else {
                inv.status = Status.ESCALATED;
                emit Escalated(invocationId, "output mismatch");
            }
        } else {
            inv.status = Status.PARTIAL_REVEAL;
        }
    }

    function markCommitTimeout(uint256 invocationId) external nonReentrant {
        Invocation storage inv = _layout().invocations[invocationId];
        if (inv.status == Status.NONE) {
            revert UnknownInvocation();
        }
        if (inv.status != Status.DISPATCHED && inv.status != Status.PARTIAL_COMMIT) {
            revert WrongStatus();
        }
        if (block.timestamp < inv.commitDeadline) {
            revert CommitDeadlineNotPassed();
        }
        inv.status = Status.ESCALATED;
        emit Escalated(invocationId, "commit timeout");
    }

    function markRevealTimeout(uint256 invocationId) external nonReentrant {
        Invocation storage inv = _layout().invocations[invocationId];
        if (inv.status == Status.NONE) {
            revert UnknownInvocation();
        }
        if (inv.status != Status.BOTH_COMMITTED && inv.status != Status.PARTIAL_REVEAL) {
            revert WrongStatus();
        }
        if (block.timestamp < inv.revealDeadline) {
            revert RevealDeadlineNotPassed();
        }
        inv.status = Status.ESCALATED;
        emit Escalated(invocationId, "reveal timeout");
    }

    function statusOf(uint256 invocationId) external view returns (Status) {
        return _layout().invocations[invocationId].status;
    }

    function verifiedOutput(uint256 invocationId) external view returns (bytes32) {
        Invocation storage inv = _layout().invocations[invocationId];
        if (inv.status != Status.VERIFIED) {
            return bytes32(0);
        }
        return inv.executorOutput;
    }

    function invocation(uint256 invocationId) external view returns (Invocation memory) {
        return _layout().invocations[invocationId];
    }

    function commitDigest(Role role, address node, bytes32 outputHandle, bytes32 salt) external pure returns (bytes32) {
        return _commitDigest(role, node, outputHandle, salt);
    }

    function _commitDigest(Role role, address node, bytes32 outputHandle, bytes32 salt) private pure returns (bytes32) {
        return keccak256(abi.encodePacked(uint8(role), node, outputHandle, salt));
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
