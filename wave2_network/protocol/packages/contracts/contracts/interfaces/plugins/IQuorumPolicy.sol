// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";

interface IQuorumPolicy is IERC165 {
    function selectQuorum(uint256 modelId, bytes calldata input) external view returns (bytes32 quorumId);
}
