// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {IModelBinding} from "./IModelBinding.sol";

interface IAgentPolicy is IERC165 {
    function plan(bytes calldata input) external view returns (IModelBinding[] memory ordered);
    function combine(bytes[] calldata modelOutputs) external view returns (bytes memory);
}
