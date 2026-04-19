// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Script, console2} from "forge-std/Script.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {AgentConfigRegistry} from "@blindference/contracts/core/AgentConfigRegistry.sol";
import {ExecutionCommitmentRegistry} from "@blindference/contracts/core/ExecutionCommitmentRegistry.sol";
import {NodeAttestationRegistry} from "@blindference/contracts/core/NodeAttestationRegistry.sol";
import {IAgentConfigRegistry} from "@blindference/contracts/interfaces/core/IAgentConfigRegistry.sol";

import {StaticModelBinding} from "@blindference/contracts/plugins/bindings/StaticModelBinding.sol";
import {SinglePlanCombineIdentity} from "@blindference/contracts/plugins/bindings/SinglePlanCombineIdentity.sol";
import {FixedQuorumPolicy} from "@blindference/contracts/plugins/bindings/FixedQuorumPolicy.sol";

import {MockAgentIdentityRegistry} from "@blindference/contracts/mocks/MockAgentIdentityRegistry.sol";
import {MockEscrowReleaser} from "@blindference/contracts/mocks/MockEscrowReleaser.sol";
import {PricingConfig} from "@blindference/contracts/common/Types.sol";

import {TradingSignalAttestor} from "../contracts/core/TradingSignalAttestor.sol";
import {TradingLossUnderwriter} from "../contracts/core/TradingLossUnderwriter.sol";
import {MockPriceOracle} from "../contracts/mocks/MockPriceOracle.sol";

/// @notice End-to-end agent compilation script. Demonstrates the four
///         assembly stages that turn a pile of deployed contracts into a
///         working Blindference agent:
///
///   Stage 1 — deploy code: protocol contracts + example contracts
///   Stage 2 — register agent identity (ERC-8004 in MockAgentIdentityRegistry)
///   Stage 3 — COMPILE: write the agent's slot composition into AgentConfigRegistry
///   Stage 4 — node attestations (left to operators; not done here)
///
/// Stage 3 is the "agent compiling" moment — every time it runs, the
/// AgentConfig version bumps and the agent's behavior changes.
contract DeployTradingAgentScript is Script {
    struct Deployment {
        // Stage 1 — protocol
        AgentConfigRegistry agentConfig;
        ExecutionCommitmentRegistry ecr;
        NodeAttestationRegistry attestations;
        MockAgentIdentityRegistry identity;
        MockEscrowReleaser escrow;
        // Stage 1 — generic plugins (reference impls)
        StaticModelBinding modelBinding;
        SinglePlanCombineIdentity agentPolicy;
        FixedQuorumPolicy quorumPolicy;
        // Stage 1 — trading-vertical
        TradingSignalAttestor signalAttestor;
        TradingLossUnderwriter lossUnderwriter;
        MockPriceOracle priceOracle;
    }

    struct AgentConfig {
        uint256 agentId;
        address agentWallet;
        uint256 modelId;
        bytes32 quorumId;
        PricingConfig pricing;
    }

    function run() external {
        AgentConfig memory cfg = AgentConfig({
            agentId: vm.envOr("AGENT_ID", uint256(1)),
            agentWallet: vm.envOr("AGENT_WALLET", msg.sender),
            modelId: vm.envOr("MODEL_ID", uint256(101)),
            quorumId: vm.envOr("QUORUM_ID", bytes32(uint256(0xC0DE))),
            pricing: PricingConfig({baseFee: 5e5, maxModelSpend: 5e6, premiumCap: 1e6})
        });

        vm.startBroadcast();

        Deployment memory d = _deployStage1(cfg);
        _stage2_registerAgentIdentity(d, cfg);
        _stage3_compileAgent(d, cfg);

        vm.stopBroadcast();

        _summary(d, cfg);
    }

    function _deployStage1(AgentConfig memory cfg) internal returns (Deployment memory d) {
        address dispatcher = msg.sender;

        d.identity = new MockAgentIdentityRegistry();
        d.escrow = new MockEscrowReleaser();
        d.priceOracle = new MockPriceOracle();

        AgentConfigRegistry agentImpl = new AgentConfigRegistry(address(0));
        d.agentConfig = AgentConfigRegistry(
            address(
                new ERC1967Proxy(
                    address(agentImpl), abi.encodeCall(AgentConfigRegistry.initialize, (msg.sender, address(d.identity)))
                )
            )
        );

        ExecutionCommitmentRegistry ecrImpl = new ExecutionCommitmentRegistry(address(0));
        d.ecr = ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(ecrImpl), abi.encodeCall(ExecutionCommitmentRegistry.initialize, (msg.sender, dispatcher))
                )
            )
        );

        NodeAttestationRegistry attImpl = new NodeAttestationRegistry(address(0));
        d.attestations = NodeAttestationRegistry(
            address(
                new ERC1967Proxy(address(attImpl), abi.encodeCall(NodeAttestationRegistry.initialize, (msg.sender)))
            )
        );

        d.modelBinding = new StaticModelBinding(cfg.modelId, 7, cfg.pricing);
        d.agentPolicy = new SinglePlanCombineIdentity(d.modelBinding);
        d.quorumPolicy = new FixedQuorumPolicy(cfg.quorumId);

        TradingSignalAttestor sigImpl = new TradingSignalAttestor(address(0));
        d.signalAttestor = TradingSignalAttestor(
            address(
                new ERC1967Proxy(
                    address(sigImpl), abi.encodeCall(TradingSignalAttestor.initialize, (msg.sender, address(d.ecr)))
                )
            )
        );

        TradingLossUnderwriter uwImpl = new TradingLossUnderwriter(address(0));
        d.lossUnderwriter = TradingLossUnderwriter(
            address(
                new ERC1967Proxy(
                    address(uwImpl),
                    abi.encodeCall(
                        TradingLossUnderwriter.initialize,
                        (
                            msg.sender,
                            address(d.signalAttestor),
                            address(d.priceOracle),
                            address(d.escrow),
                            uint256(200), // 2% loss threshold
                            uint256(100) // 1% HOLD tolerance
                        )
                    )
                )
            )
        );
    }

    function _stage2_registerAgentIdentity(Deployment memory d, AgentConfig memory cfg) internal {
        d.identity.register(cfg.agentId, cfg.agentWallet);
    }

    /// @notice Stage 3 — THIS is "agent compiling".
    ///         Writes the agent's full slot composition on-chain. Versioned;
    ///         re-running this updates behavior atomically.
    function _stage3_compileAgent(Deployment memory d, AgentConfig memory cfg) internal {
        address[] memory models = new address[](1);
        models[0] = address(d.modelBinding);

        address[] memory inputConditions = new address[](0);
        address[] memory outputConditions = new address[](0);

        // The trading-vertical contracts (TradingSignalAttestor, TradingLossUnderwriter)
        // sit OUTSIDE the slot model in this example — they are integrators of
        // the protocol, not slot plugins. The slots stay generic so the agent
        // is a vanilla Blindference agent that publishes a bytes32 verdict;
        // the trading layer reads that verdict and acts on it.
        address[] memory executions = new address[](0);
        address[] memory underwriters = new address[](0);

        bytes32[] memory ticketModes = new bytes32[](1);
        ticketModes[0] = keccak256("per-call");

        IAgentConfigRegistry.AgentConfig memory agentSlots = IAgentConfigRegistry.AgentConfig({
            wallet: cfg.agentWallet,
            pricing: cfg.pricing,
            models: models,
            agentPolicy: address(d.agentPolicy),
            quorumPolicy: address(d.quorumPolicy),
            inputConditions: inputConditions,
            outputConditions: outputConditions,
            executions: executions,
            underwriters: underwriters,
            ticketModes: ticketModes,
            version: 0
        });

        // Must be called from cfg.agentWallet for the on-chain owner check.
        // In a forge script this requires `--sender $AGENT_WALLET --account $AGENT_KEY`,
        // OR the agent wallet broadcasting separately after stage 2.
        d.agentConfig.configure(cfg.agentId, agentSlots);
    }

    function _summary(Deployment memory d, AgentConfig memory cfg) internal pure {
        console2.log("\n=== Agent compiled ===");
        console2.log("agentId:           ", cfg.agentId);
        console2.log("agentWallet:       ", cfg.agentWallet);
        console2.log("modelId:           ", cfg.modelId);
        console2.log("");
        console2.log("=== Protocol ===");
        console2.log("AgentConfigRegistry: ", address(d.agentConfig));
        console2.log("ExecutionCommitmentRegistry:", address(d.ecr));
        console2.log("NodeAttestationRegistry: ", address(d.attestations));
        console2.log("AgentIdentityRegistry (mock):", address(d.identity));
        console2.log("EscrowReleaser (mock):", address(d.escrow));
        console2.log("");
        console2.log("=== Slot plugins ===");
        console2.log("StaticModelBinding:    ", address(d.modelBinding));
        console2.log("SinglePlanCombineIdentity:", address(d.agentPolicy));
        console2.log("FixedQuorumPolicy:     ", address(d.quorumPolicy));
        console2.log("");
        console2.log("=== Trading vertical ===");
        console2.log("TradingSignalAttestor: ", address(d.signalAttestor));
        console2.log("TradingLossUnderwriter:", address(d.lossUnderwriter));
        console2.log("MockPriceOracle:       ", address(d.priceOracle));
    }
}
