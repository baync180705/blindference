// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IRewardAccumulator} from "../interfaces/core/IRewardAccumulator.sol";
import {IReputationRegistry} from "../interfaces/core/IReputationRegistry.sol";
import {IEscrowReleaser} from "../interfaces/external/IEscrowReleaser.sol";

contract RewardAccumulator is TestnetCoreBase, IRewardAccumulator {
    /// @custom:storage-location erc7201:blindference.RewardAccumulator
    struct Layout {
        IReputationRegistry reputation;
        IEscrowReleaser escrowReleaser;
        uint64 minWorkPerCycle;
        uint64 minValidationPerCycle;

        mapping(address accruer => bool) authorized;
        mapping(address node => mapping(uint64 cycleEpoch => AccruedItem[])) items;
        mapping(address node => mapping(uint64 cycleEpoch => uint64)) workCounts;
        mapping(address node => mapping(uint64 cycleEpoch => uint64)) validationCounts;
        mapping(address node => mapping(uint64 cycleEpoch => bool)) released;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xe7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e700;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(
        address owner_,
        address reputation_,
        address escrowReleaser_,
        uint64 minWorkPerCycle_,
        uint64 minValidationPerCycle_
    ) external initializer {
        require(reputation_ != address(0) && escrowReleaser_ != address(0), "ZeroAddress");
        __TestnetCoreBase_init(owner_);
        Layout storage l = _layout();
        l.reputation = IReputationRegistry(reputation_);
        l.escrowReleaser = IEscrowReleaser(escrowReleaser_);
        l.minWorkPerCycle = minWorkPerCycle_;
        l.minValidationPerCycle = minValidationPerCycle_;
    }

    function setAccruer(address accruer, bool ok) external onlyOwner {
        _layout().authorized[accruer] = ok;
    }

    function isAccruer(address accruer) external view returns (bool) {
        return _layout().authorized[accruer];
    }

    function accrue(address node, uint64 cycleEpoch, uint256 escrowId, WorkRole role, uint256 amount, bytes32 workRef)
        external
        nonReentrant
    {
        Layout storage l = _layout();
        if (!l.authorized[_msgSender()]) {
            revert NotAuthorizedAccruer();
        }
        if (amount == 0) {
            revert ZeroAmount();
        }

        l.items[node][cycleEpoch].push(
            AccruedItem({escrowId: escrowId, amount: amount, workRef: workRef, role: role, status: ItemStatus.ACCRUED})
        );

        if (role == WorkRole.EXECUTOR || role == WorkRole.CROSS_VERIFIER) {
            unchecked {
                l.workCounts[node][cycleEpoch] += 1;
            }
        } else {
            unchecked {
                l.validationCounts[node][cycleEpoch] += 1;
            }
        }

        emit Accrued(node, cycleEpoch, escrowId, role, amount, workRef);
    }

    function release(address node, uint64 cycleEpoch) external nonReentrant {
        Layout storage l = _layout();
        if (cycleEpoch >= l.reputation.currentCycle()) {
            revert CycleNotEnded();
        }
        if (l.released[node][cycleEpoch]) {
            revert AlreadyReleased();
        }

        AccruedItem[] storage items = l.items[node][cycleEpoch];
        if (items.length == 0) {
            revert NoPendingItems();
        }

        if (l.reputation.isGuiltyInCycle(node, cycleEpoch)) {
            revert AccuracyFailed();
        }
        if (l.workCounts[node][cycleEpoch] < l.minWorkPerCycle) {
            revert WorkProportionFailed();
        }
        if (l.validationCounts[node][cycleEpoch] < l.minValidationPerCycle) {
            revert ValidationProportionFailed();
        }

        l.released[node][cycleEpoch] = true;

        uint256 total = 0;
        uint256 count = items.length;
        for (uint256 i = 0; i < count; i++) {
            AccruedItem storage item = items[i];
            if (item.status != ItemStatus.ACCRUED) {
                continue;
            }
            item.status = ItemStatus.RELEASED;
            total += item.amount;
            l.escrowReleaser.release(item.escrowId, node, item.amount);
        }

        emit Released(node, cycleEpoch, total, count);
    }

    function forfeit(address node, uint64 cycleEpoch) external nonReentrant {
        Layout storage l = _layout();
        if (!l.authorized[_msgSender()]) {
            revert NotAuthorizedAccruer();
        }
        if (l.released[node][cycleEpoch]) {
            revert AlreadyReleased();
        }

        AccruedItem[] storage items = l.items[node][cycleEpoch];
        uint256 count = items.length;
        if (count == 0) {
            revert NoPendingItems();
        }

        l.released[node][cycleEpoch] = true;
        for (uint256 i = 0; i < count; i++) {
            if (items[i].status == ItemStatus.ACCRUED) {
                items[i].status = ItemStatus.FORFEITED;
            }
        }

        emit Forfeited(node, cycleEpoch, count);
    }

    function pendingItems(address node, uint64 cycleEpoch) external view returns (AccruedItem[] memory) {
        return _layout().items[node][cycleEpoch];
    }

    function pendingTotal(address node, uint64 cycleEpoch) external view returns (uint256 total) {
        AccruedItem[] storage items = _layout().items[node][cycleEpoch];
        for (uint256 i = 0; i < items.length; i++) {
            if (items[i].status == ItemStatus.ACCRUED) {
                total += items[i].amount;
            }
        }
    }

    function workCount(address node, uint64 cycleEpoch) external view returns (uint64) {
        return _layout().workCounts[node][cycleEpoch];
    }

    function validationCount(address node, uint64 cycleEpoch) external view returns (uint64) {
        return _layout().validationCounts[node][cycleEpoch];
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
