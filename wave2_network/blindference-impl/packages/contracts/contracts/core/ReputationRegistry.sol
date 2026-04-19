// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IReputationRegistry} from "../interfaces/core/IReputationRegistry.sol";
import {IArbiterSelectionRegistry as IASR} from "../interfaces/core/IArbiterSelectionRegistry.sol";
import {IExecutionCommitmentRegistry as IECR} from "../interfaces/core/IExecutionCommitmentRegistry.sol";

contract ReputationRegistry is TestnetCoreBase, IReputationRegistry {
    /// @custom:storage-location erc7201:blindference.ReputationRegistry
    struct Layout {
        IASR arbiterRegistry;
        IECR executionRegistry;
        uint64 cycleDuration;

        mapping(address node => Reputation) reputations;
        mapping(address node => mapping(uint64 cycleEpoch => bool)) guiltyInCycle;
        mapping(address node => mapping(uint64 cycleEpoch => bool)) creditedInCycle;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xd5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d500;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_, address arbiterRegistry_, address executionRegistry_, uint64 cycleDuration_)
        external
        initializer
    {
        require(arbiterRegistry_ != address(0) && executionRegistry_ != address(0), "ZeroAddress");
        require(cycleDuration_ > 0, "ZeroCycle");
        __TestnetCoreBase_init(owner_);
        Layout storage l = _layout();
        l.arbiterRegistry = IASR(arbiterRegistry_);
        l.executionRegistry = IECR(executionRegistry_);
        l.cycleDuration = cycleDuration_;
    }

    function recordFraudFromArbitration(uint256 invocationId, address node, FraudReason reason) external nonReentrant {
        Layout storage l = _layout();
        IASR.Arbitration memory a = l.arbiterRegistry.arbitrationOf(invocationId);
        if (a.status != IASR.ArbitrationStatus.RESOLVED_MAJORITY) {
            revert NoArbitrationMajority();
        }

        bool guilty = _isGuilty(l, invocationId, a, node, reason);
        if (!guilty) {
            revert NodeNotOnLosingSide();
        }

        uint64 cycle = currentCycle();
        if (l.guiltyInCycle[node][cycle]) {
            revert AlreadyResetThisCycle();
        }
        l.guiltyInCycle[node][cycle] = true;

        Reputation storage rep = l.reputations[node];
        rep.score = 0;
        rep.cycleResetAt = cycle;
        rep.cyclesGuilty += 1;

        emit FraudRecorded(node, invocationId, reason);
    }

    function recordHonestCycle(address node, uint64 cycleEpoch) external nonReentrant {
        Layout storage l = _layout();
        if (cycleEpoch >= currentCycle()) {
            revert CycleNotEnded();
        }
        if (l.guiltyInCycle[node][cycleEpoch]) {
            revert AlreadyResetThisCycle();
        }
        if (l.creditedInCycle[node][cycleEpoch]) {
            revert AlreadyCreditedThisCycle();
        }
        l.creditedInCycle[node][cycleEpoch] = true;

        Reputation storage rep = l.reputations[node];
        unchecked {
            rep.score += 1;
            rep.cyclesActive += 1;
        }

        emit HonestCycleRecorded(node, cycleEpoch, rep.score);
    }

    function reputationOf(address node) external view returns (Reputation memory) {
        return _layout().reputations[node];
    }

    function arbitrationFrequencyBps(address node) external view returns (uint16) {
        uint64 score = _layout().reputations[node].score;
        if (score == 0) {
            return 10_000;
        }
        if (score < 10) {
            return 5_000;
        }
        if (score < 50) {
            return 1_000;
        }
        if (score < 100) {
            return 500;
        }
        if (score < 500) {
            return 100;
        }
        return 25;
    }

    function isGuiltyInCycle(address node, uint64 cycleEpoch) external view returns (bool) {
        return _layout().guiltyInCycle[node][cycleEpoch];
    }

    function currentCycle() public view returns (uint64) {
        return uint64(block.timestamp / _layout().cycleDuration);
    }

    function _isGuilty(
        Layout storage l,
        uint256 invocationId,
        IASR.Arbitration memory a,
        address node,
        FraudReason reason
    ) private view returns (bool) {
        if (reason == FraudReason.ARBITER_MINORITY || reason == FraudReason.ARBITER_NO_REVEAL) {
            bool isArbiter = false;
            for (uint256 i = 0; i < a.arbiters.length; i++) {
                if (a.arbiters[i] == node) {
                    isArbiter = true;
                    break;
                }
            }
            if (!isArbiter) {
                return false;
            }

            bytes32 reveal = l.arbiterRegistry.revealOf(invocationId, node);
            if (reason == FraudReason.ARBITER_NO_REVEAL) {
                return reveal == bytes32(0);
            }
            return reveal != bytes32(0) && reveal != a.majorityOutput;
        }

        IECR.Invocation memory inv = l.executionRegistry.invocation(invocationId);

        if (reason == FraudReason.EXECUTOR_WRONG) {
            return inv.executor == node && inv.executorRevealed && inv.executorOutput != a.majorityOutput;
        }
        if (reason == FraudReason.VERIFIER_WRONG) {
            return inv.crossVerifier == node && inv.verifierRevealed && inv.verifierOutput != a.majorityOutput;
        }
        if (reason == FraudReason.EXECUTOR_NO_REVEAL) {
            return inv.executor == node && !inv.executorRevealed;
        }
        if (reason == FraudReason.VERIFIER_NO_REVEAL) {
            return inv.crossVerifier == node && !inv.verifierRevealed;
        }

        return false;
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
