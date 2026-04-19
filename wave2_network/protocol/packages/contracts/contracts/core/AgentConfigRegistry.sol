// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IAgentConfigRegistry} from "../interfaces/core/IAgentConfigRegistry.sol";
import {IAgentIdentityRegistry} from "../interfaces/external/IAgentIdentityRegistry.sol";

contract AgentConfigRegistry is TestnetCoreBase, IAgentConfigRegistry {
    /// @custom:storage-location erc7201:reineira.blindference.AgentConfigRegistry
    struct Layout {
        IAgentIdentityRegistry identity;
        mapping(uint256 agentId => AgentConfig) configs;
    }

    bytes32 private constant _LAYOUT_SLOT = 0x9d3a2f8e0f4b1c6a8e2d7f0b9c1a3e5d7f2b4c6a8e0d2f4b6a8c0e2d4f6a8c00;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_, address identity_) external initializer {
        if (identity_ == address(0)) {
            revert InvalidConfig();
        }
        __TestnetCoreBase_init(owner_);
        _layout().identity = IAgentIdentityRegistry(identity_);
    }

    function configure(uint256 agentId, AgentConfig calldata cfg) external nonReentrant {
        Layout storage l = _layout();

        address wallet = l.identity.walletOf(agentId);
        if (wallet == address(0)) {
            revert UnknownAgent();
        }
        if (_msgSender() != wallet) {
            revert NotAgentWallet();
        }
        if (cfg.wallet != wallet) {
            revert InvalidConfig();
        }
        if (cfg.agentPolicy == address(0)) {
            revert InvalidConfig();
        }
        if (cfg.quorumPolicy == address(0)) {
            revert InvalidConfig();
        }

        AgentConfig storage stored = l.configs[agentId];
        uint64 nextVersion;
        unchecked {
            nextVersion = stored.version + 1;
        }

        l.configs[agentId] = cfg;
        l.configs[agentId].version = nextVersion;

        emit AgentConfigured(agentId, nextVersion);
    }

    function configOf(uint256 agentId) external view returns (AgentConfig memory) {
        return _layout().configs[agentId];
    }

    function versionOf(uint256 agentId) external view returns (uint64) {
        return _layout().configs[agentId].version;
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
