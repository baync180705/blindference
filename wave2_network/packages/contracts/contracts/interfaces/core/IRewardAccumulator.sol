// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface IRewardAccumulator {
    enum WorkRole {
        EXECUTOR,
        CROSS_VERIFIER,
        ARBITER
    }

    enum ItemStatus {
        ACCRUED,
        RELEASED,
        FORFEITED
    }

    struct AccruedItem {
        uint256 escrowId;
        uint256 amount;
        bytes32 workRef;
        WorkRole role;
        ItemStatus status;
    }

    event Accrued(
        address indexed node,
        uint64 indexed cycleEpoch,
        uint256 indexed escrowId,
        WorkRole role,
        uint256 amount,
        bytes32 workRef
    );
    event Released(address indexed node, uint64 indexed cycleEpoch, uint256 totalAmount, uint256 itemCount);
    event Forfeited(address indexed node, uint64 indexed cycleEpoch, uint256 itemCount);

    error NotAuthorizedAccruer();
    error NoPendingItems();
    error CycleNotEnded();
    error AlreadyReleased();
    error AccuracyFailed();
    error WorkProportionFailed();
    error ValidationProportionFailed();
    error ZeroAmount();

    function accrue(address node, uint64 cycleEpoch, uint256 escrowId, WorkRole role, uint256 amount, bytes32 workRef)
        external;

    function release(address node, uint64 cycleEpoch) external;
    function forfeit(address node, uint64 cycleEpoch) external;

    function pendingItems(address node, uint64 cycleEpoch) external view returns (AccruedItem[] memory);
    function pendingTotal(address node, uint64 cycleEpoch) external view returns (uint256);
    function workCount(address node, uint64 cycleEpoch) external view returns (uint64);
    function validationCount(address node, uint64 cycleEpoch) external view returns (uint64);
}
