// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IAgentIdentityRegistry} from "../interfaces/external/IAgentIdentityRegistry.sol";

contract MockAgentIdentityRegistry is IAgentIdentityRegistry {
    mapping(uint256 agentId => address) private _wallets;
    mapping(address wallet => uint256) private _ids;

    function register(uint256 agentId, address wallet) external {
        _wallets[agentId] = wallet;
        _ids[wallet] = agentId;
    }

    function walletOf(uint256 agentId) external view returns (address) {
        return _wallets[agentId];
    }

    function agentIdOf(address wallet) external view returns (uint256) {
        return _ids[wallet];
    }
}
