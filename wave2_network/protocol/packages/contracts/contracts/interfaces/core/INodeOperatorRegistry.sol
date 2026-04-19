// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface INodeOperatorRegistry {
    function modelExecutorAuthorized(address node, uint256 modelId) external view returns (bool);
}
