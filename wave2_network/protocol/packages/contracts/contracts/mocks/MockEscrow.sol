// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {euint64} from "@fhenixprotocol/cofhe-contracts/FHE.sol";

interface IEscrowMinimal {
    function hasBudget(uint256 escrowId, address claimant, euint64 amount) external view returns (bool);
    function release(uint256 escrowId, address recipient, euint64 amount) external;
}

contract MockEscrow is IEscrowMinimal {
    mapping(uint256 escrowId => bool) private _hasBudget;

    event ReleaseRequested(uint256 indexed escrowId, address indexed recipient);

    function setBudget(uint256 escrowId, bool ok) external {
        _hasBudget[escrowId] = ok;
    }

    function hasBudget(uint256 escrowId, address, euint64) external view returns (bool) {
        return _hasBudget[escrowId];
    }

    function release(uint256 escrowId, address recipient, euint64) external {
        emit ReleaseRequested(escrowId, recipient);
    }
}
