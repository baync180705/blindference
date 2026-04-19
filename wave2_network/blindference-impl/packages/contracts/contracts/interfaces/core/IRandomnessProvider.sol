// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface IRandomnessProvider {
    /// @notice Returns randomness derived from `seed` and chain entropy.
    /// @dev Implementations must be unpredictable in advance to a caller who
    ///      doesn't know `seed`. The default impl uses `block.prevrandao` plus
    ///      the prior block hash. A Chainlink-VRF-backed impl can be swapped
    ///      in for stronger guarantees.
    function randomness(bytes32 seed) external view returns (bytes32);
}
