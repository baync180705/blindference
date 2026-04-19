// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IEscrowReleaser} from "../interfaces/external/IEscrowReleaser.sol";

contract MockEscrowReleaser is IEscrowReleaser {
    struct ReleaseCall {
        uint256 escrowId;
        address recipient;
        uint256 amount;
    }

    ReleaseCall[] public calls;

    event MockReleaseCalled(uint256 indexed escrowId, address indexed recipient, uint256 amount);

    function release(uint256 escrowId, address recipient, uint256 amount) external {
        calls.push(ReleaseCall(escrowId, recipient, amount));
        emit MockReleaseCalled(escrowId, recipient, amount);
    }

    function callCount() external view returns (uint256) {
        return calls.length;
    }
}
