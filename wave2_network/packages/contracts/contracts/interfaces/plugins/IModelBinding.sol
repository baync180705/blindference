// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {PricingConfig} from "../../common/Types.sol";

interface IModelBinding is IERC165 {
    function modelId() external view returns (uint256);
    function pricing() external view returns (PricingConfig memory);
    function requiredQuorumSize() external view returns (uint8);
}
