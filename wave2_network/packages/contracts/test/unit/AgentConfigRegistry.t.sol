// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {AgentConfigRegistry} from "../../contracts/core/AgentConfigRegistry.sol";
import {IAgentConfigRegistry} from "../../contracts/interfaces/core/IAgentConfigRegistry.sol";
import {MockAgentIdentityRegistry} from "../../contracts/mocks/MockAgentIdentityRegistry.sol";
import {PricingConfig} from "../../contracts/common/Types.sol";

contract AgentConfigRegistryTest is Test {
    AgentConfigRegistry public registry;
    MockAgentIdentityRegistry public identity;

    address public owner = makeAddr("owner");
    address public agentWallet = makeAddr("agentWallet");
    address public attacker = makeAddr("attacker");
    uint256 public constant AGENT_ID = 42;

    function setUp() public {
        identity = new MockAgentIdentityRegistry();
        identity.register(AGENT_ID, agentWallet);

        AgentConfigRegistry impl = new AgentConfigRegistry(address(0));
        registry = AgentConfigRegistry(
            address(
                new ERC1967Proxy(
                    address(impl), abi.encodeCall(AgentConfigRegistry.initialize, (owner, address(identity)))
                )
            )
        );
    }

    function _baseConfig() internal returns (IAgentConfigRegistry.AgentConfig memory cfg) {
        cfg.wallet = agentWallet;
        cfg.pricing = PricingConfig({baseFee: 1, maxModelSpend: 2, premiumCap: 0});
        cfg.models = new address[](1);
        cfg.models[0] = makeAddr("modelBinding");
        cfg.agentPolicy = makeAddr("agentPolicy");
        cfg.quorumPolicy = makeAddr("quorumPolicy");
        cfg.inputConditions = new address[](0);
        cfg.outputConditions = new address[](0);
        cfg.executions = new address[](0);
        cfg.underwriters = new address[](0);
        cfg.ticketModes = new bytes32[](1);
        cfg.ticketModes[0] = keccak256("per-call");
    }

    function test_initialize_storesIdentity() public {
        assertEq(registry.versionOf(AGENT_ID), 0);
    }

    function test_configure_succeedsFromAgentWallet() public {
        vm.prank(agentWallet);
        registry.configure(AGENT_ID, _baseConfig());

        assertEq(registry.versionOf(AGENT_ID), 1);

        IAgentConfigRegistry.AgentConfig memory stored = registry.configOf(AGENT_ID);
        assertEq(stored.wallet, agentWallet);
        assertEq(stored.agentPolicy, makeAddr("agentPolicy"));
        assertEq(stored.models.length, 1);
        assertEq(stored.version, 1);
    }

    function test_configure_revertsForUnknownAgent() public {
        IAgentConfigRegistry.AgentConfig memory cfg = _baseConfig();
        vm.expectRevert(IAgentConfigRegistry.UnknownAgent.selector);
        vm.prank(agentWallet);
        registry.configure(999, cfg);
    }

    function test_configure_revertsForNonAgentWallet() public {
        IAgentConfigRegistry.AgentConfig memory cfg = _baseConfig();
        vm.expectRevert(IAgentConfigRegistry.NotAgentWallet.selector);
        vm.prank(attacker);
        registry.configure(AGENT_ID, cfg);
    }

    function test_configure_revertsWhenWalletInConfigDiverges() public {
        IAgentConfigRegistry.AgentConfig memory cfg = _baseConfig();
        cfg.wallet = attacker;
        vm.expectRevert(IAgentConfigRegistry.InvalidConfig.selector);
        vm.prank(agentWallet);
        registry.configure(AGENT_ID, cfg);
    }

    function test_configure_revertsOnZeroAgentPolicy() public {
        IAgentConfigRegistry.AgentConfig memory cfg = _baseConfig();
        cfg.agentPolicy = address(0);
        vm.expectRevert(IAgentConfigRegistry.InvalidConfig.selector);
        vm.prank(agentWallet);
        registry.configure(AGENT_ID, cfg);
    }

    function test_configure_revertsOnZeroQuorumPolicy() public {
        IAgentConfigRegistry.AgentConfig memory cfg = _baseConfig();
        cfg.quorumPolicy = address(0);
        vm.expectRevert(IAgentConfigRegistry.InvalidConfig.selector);
        vm.prank(agentWallet);
        registry.configure(AGENT_ID, cfg);
    }

    function test_configure_bumpsVersionOnEachUpdate() public {
        vm.startPrank(agentWallet);
        registry.configure(AGENT_ID, _baseConfig());
        registry.configure(AGENT_ID, _baseConfig());
        registry.configure(AGENT_ID, _baseConfig());
        vm.stopPrank();

        assertEq(registry.versionOf(AGENT_ID), 3);
    }

    function test_configure_emitsAgentConfiguredEvent() public {
        vm.expectEmit(true, false, false, true);
        emit IAgentConfigRegistry.AgentConfigured(AGENT_ID, 1);

        vm.prank(agentWallet);
        registry.configure(AGENT_ID, _baseConfig());
    }
}
