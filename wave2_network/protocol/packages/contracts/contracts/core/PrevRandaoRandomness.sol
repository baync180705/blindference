// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IRandomnessProvider} from "../interfaces/core/IRandomnessProvider.sol";

/// @notice Default randomness source: mixes seed, block.prevrandao, prior block hash.
///         Sufficient when arbiter selection happens *after* a dispute is observed
///         on-chain — the executor cannot pre-bribe arbiters because they don't know
///         when escalation will fire. For stronger adversary models, swap in a
///         Chainlink-VRF-backed provider.
contract PrevRandaoRandomness is IRandomnessProvider {
    function randomness(bytes32 seed) external view returns (bytes32) {
        uint256 priorBlock = block.number == 0 ? 0 : block.number - 1;
        return keccak256(abi.encode(seed, block.prevrandao, blockhash(priorBlock), block.chainid));
    }
}
