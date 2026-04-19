// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IRandomnessProvider} from "../interfaces/core/IRandomnessProvider.sol";

contract MockRandomnessProvider is IRandomnessProvider {
    bytes32 private _next;

    function setNext(bytes32 value) external {
        _next = value;
    }

    function randomness(bytes32 seed) external view returns (bytes32) {
        return _next == bytes32(0) ? keccak256(abi.encode(seed)) : _next;
    }
}
