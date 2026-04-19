// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

interface IAgentIdentityRegistry {
    function walletOf(uint256 agentId) external view returns (address);
    function agentIdOf(address wallet) external view returns (uint256);
}
