// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {PricingConfig} from "../../common/Types.sol";

interface IAgentConfigRegistry {
    struct AgentConfig {
        address wallet;
        PricingConfig pricing;
        address[] models;
        address agentPolicy;
        address quorumPolicy;
        address[] inputConditions;
        address[] outputConditions;
        address[] executions;
        address[] underwriters;
        bytes32[] ticketModes;
        uint64 version;
    }

    event AgentConfigured(uint256 indexed agentId, uint64 version);

    error UnknownAgent();
    error NotAgentWallet();
    error InvalidConfig();

    function configure(uint256 agentId, AgentConfig calldata config) external;
    function configOf(uint256 agentId) external view returns (AgentConfig memory);
    function versionOf(uint256 agentId) external view returns (uint64);
}
