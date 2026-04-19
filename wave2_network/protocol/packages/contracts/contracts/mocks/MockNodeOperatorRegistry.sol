// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {INodeOperatorRegistry} from "../interfaces/core/INodeOperatorRegistry.sol";

contract MockNodeOperatorRegistry is INodeOperatorRegistry {
    mapping(address node => mapping(uint256 modelId => bool)) private _authorized;

    function authorize(address node, uint256 modelId, bool ok) external {
        _authorized[node][modelId] = ok;
    }

    function modelExecutorAuthorized(address node, uint256 modelId) external view returns (bool) {
        return _authorized[node][modelId];
    }
}
