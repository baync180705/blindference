// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

/// @notice Mirror of Reineira's escrow release surface — what the
///         Blindference RewardAccumulator calls when a node's accrued
///         reward passes all release criteria. The actual implementation
///         lives in Reineira's `IEscrow` (or `PayoutManifest` adapter).
interface IEscrowReleaser {
    function release(uint256 escrowId, address recipient, uint256 amount) external;
}
