// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

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

import {BlindferenceAttestor} from "../contracts/core/BlindferenceAttestor.sol";
import {BlindferenceUnderwriter} from "../contracts/core/BlindferenceUnderwriter.sol";
import {BlindferenceAgent} from "../contracts/core/BlindferenceAgent.sol";
import {BlindferenceInputVault} from "../contracts/core/BlindferenceInputVault.sol";
import {MockPriceOracle} from "../contracts/mocks/MockPriceOracle.sol";

contract DeployBlindferenceAgentScript is Script {
    bytes32 internal constant ETH_ASSET = keccak256("ETH/USDC");
    bytes32 internal constant BTC_ASSET = keccak256("BTC/USDC");

    struct Deployment {
        AgentConfigRegistry agentConfig;
        ExecutionCommitmentRegistry ecr;
        NodeAttestationRegistry attestations;
        MockAgentIdentityRegistry identity;
        MockEscrowReleaser escrow;
        StaticModelBinding modelBinding;
        SinglePlanCombineIdentity agentPolicy;
        FixedQuorumPolicy quorumPolicy;
        BlindferenceAttestor attestor;
        BlindferenceUnderwriter underwriter;
        BlindferenceAgent agent;
        BlindferenceInputVault inputVault;
        MockPriceOracle priceOracle;
    }

    struct AgentConfigInput {
        uint256 agentId;
        address agentWallet;
        uint256 modelId;
        bytes32 quorumId;
        string provider;
        string modelIdentifier;
        PricingConfig pricing;
    }

    function run() external {
        AgentConfigInput memory cfg = AgentConfigInput({
            agentId: vm.envOr("AGENT_ID", uint256(1)),
            agentWallet: vm.envOr("AGENT_WALLET", msg.sender),
            modelId: vm.envOr("MODEL_ID", uint256(101)),
            quorumId: vm.envOr("QUORUM_ID", bytes32(uint256(0xC0DE))),
            provider: vm.envOr("MODEL_PROVIDER", string("groq")),
            modelIdentifier: vm.envOr(
                "MODEL_IDENTIFIER",
                string("groq:llama-3.3-70b-versatile")
            ),
            pricing: PricingConfig({
                baseFee: 5e5,
                maxModelSpend: 5e6,
                premiumCap: 1e6
            })
        });

        vm.startBroadcast();

        Deployment memory d = _deploy(cfg);
        _registerAgentIdentity(d, cfg);
        _compileAgent(d, cfg);

        vm.stopBroadcast();

        _summary(d, cfg);
    }

    function _deploy(
        AgentConfigInput memory cfg
    ) internal returns (Deployment memory d) {
        address dispatcher = msg.sender;

        d.identity = _identityRegistry();
        d.escrow = _escrowReleaser();
        d.priceOracle = new MockPriceOracle();
        d.inputVault = _inputVault();
        d.priceOracle.setLatest(ETH_ASSET, 3_000e8);
        d.priceOracle.setLatest(BTC_ASSET, 60_000e8);
        d.priceOracle.setDefaultOutcome("loan_demo_safe", false);
        d.priceOracle.setDefaultOutcome("loan_demo_risky", true);

        d.agentConfig = _agentConfigRegistry(address(d.identity));
        d.ecr = _executionRegistry(dispatcher);
        d.attestations = _nodeAttestationRegistry();

        d.modelBinding = new StaticModelBinding(cfg.modelId, 7, cfg.pricing);
        d.agentPolicy = new SinglePlanCombineIdentity(d.modelBinding);
        d.quorumPolicy = new FixedQuorumPolicy(cfg.quorumId);

        BlindferenceAttestor attestorImpl = new BlindferenceAttestor(
            address(0)
        );
        d.attestor = BlindferenceAttestor(
            address(
                new ERC1967Proxy(
                    address(attestorImpl),
                    abi.encodeCall(
                        BlindferenceAttestor.initialize,
                        (msg.sender, address(d.ecr))
                    )
                )
            )
        );

        BlindferenceUnderwriter underwriterImpl = new BlindferenceUnderwriter(
            address(0)
        );
        d.underwriter = BlindferenceUnderwriter(
            address(
                new ERC1967Proxy(
                    address(underwriterImpl),
                    abi.encodeCall(
                        BlindferenceUnderwriter.initialize,
                        (
                            msg.sender,
                            address(d.attestor),
                            address(d.priceOracle),
                            address(d.escrow)
                        )
                    )
                )
            )
        );

        d.agent = new BlindferenceAgent(
            msg.sender,
            "Blindference Demo Agent",
            cfg.provider,
            cfg.modelIdentifier,
            address(d.attestor),
            address(d.underwriter)
        );
    }

    function _registerAgentIdentity(
        Deployment memory d,
        AgentConfigInput memory cfg
    ) internal {
        address currentWallet = d.identity.walletOf(cfg.agentId);
        if (currentWallet != cfg.agentWallet) {
            d.identity.register(cfg.agentId, cfg.agentWallet);
        }
    }

    function _compileAgent(
        Deployment memory d,
        AgentConfigInput memory cfg
    ) internal {
        address[] memory models = new address[](1);
        models[0] = address(d.modelBinding);

        address[] memory inputConditions = new address[](0);
        address[] memory outputConditions = new address[](0);
        address[] memory executions = new address[](0);
        address[] memory underwriters = new address[](0);

        bytes32[] memory ticketModes = new bytes32[](1);
        ticketModes[0] = keccak256("per-call");

        IAgentConfigRegistry.AgentConfig
            memory agentSlots = IAgentConfigRegistry.AgentConfig({
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

        d.agentConfig.configure(cfg.agentId, agentSlots);
    }

    function _summary(
        Deployment memory d,
        AgentConfigInput memory cfg
    ) internal pure {
        console2.log("\n=== Blindference agent compiled ===");
        console2.log("agentId:", cfg.agentId);
        console2.log("agentWallet:", cfg.agentWallet);
        console2.log("provider:", cfg.provider);
        console2.log("modelIdentifier:", cfg.modelIdentifier);
        console2.log("");
        console2.log("=== Protocol ===");
        console2.log("AgentConfigRegistry:", address(d.agentConfig));
        console2.log("ExecutionCommitmentRegistry:", address(d.ecr));
        console2.log("NodeAttestationRegistry:", address(d.attestations));
        console2.log("AgentIdentityRegistry:", address(d.identity));
        console2.log("EscrowReleaser:", address(d.escrow));
        console2.log("");
        console2.log("=== Vertical ===");
        console2.log("BlindferenceAgent:", address(d.agent));
        console2.log("BlindferenceAttestor:", address(d.attestor));
        console2.log("BlindferenceUnderwriter:", address(d.underwriter));
        console2.log("BlindferenceInputVault:", address(d.inputVault));
        console2.log("MockPriceOracle:", address(d.priceOracle));
        console2.log("ETH/USDC initial price:", uint256(3_000e8));
        console2.log("BTC/USDC initial price:", uint256(60_000e8));
        console2.log("loan_demo_safe default outcome:", uint256(0));
        console2.log("loan_demo_risky default outcome:", uint256(1));
    }

    function _inputVault() internal returns (BlindferenceInputVault vault) {
        address configured = _envAddressOrZero("BLINDFERENCE_INPUT_VAULT_ADDRESS");
        if (configured != address(0)) {
            return BlindferenceInputVault(configured);
        }

        vault = new BlindferenceInputVault();
    }

    function _agentConfigRegistry(
        address identityAddress
    ) internal returns (AgentConfigRegistry registry) {
        address configured = _envAddressOrZero("AGENT_CONFIG_REGISTRY_ADDRESS");
        if (configured != address(0)) {
            return AgentConfigRegistry(configured);
        }

        AgentConfigRegistry agentImpl = new AgentConfigRegistry(address(0));
        registry = AgentConfigRegistry(
            address(
                new ERC1967Proxy(
                    address(agentImpl),
                    abi.encodeCall(
                        AgentConfigRegistry.initialize,
                        (msg.sender, identityAddress)
                    )
                )
            )
        );
    }

    function _executionRegistry(
        address dispatcher
    ) internal returns (ExecutionCommitmentRegistry registry) {
        address configured = _envAddressOrZero(
            "EXECUTION_COMMITMENT_REGISTRY_ADDRESS"
        );
        if (configured != address(0)) {
            return ExecutionCommitmentRegistry(configured);
        }

        ExecutionCommitmentRegistry implementation = new ExecutionCommitmentRegistry(
                address(0)
            );
        registry = ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(
                        ExecutionCommitmentRegistry.initialize,
                        (msg.sender, dispatcher)
                    )
                )
            )
        );
    }

    function _nodeAttestationRegistry()
        internal
        returns (NodeAttestationRegistry registry)
    {
        address configured = _envAddressOrZero(
            "NODE_ATTESTATION_REGISTRY_ADDRESS"
        );
        if (configured != address(0)) {
            return NodeAttestationRegistry(configured);
        }

        NodeAttestationRegistry implementation = new NodeAttestationRegistry(
            address(0)
        );
        registry = NodeAttestationRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(
                        NodeAttestationRegistry.initialize,
                        (msg.sender)
                    )
                )
            )
        );
    }

    function _identityRegistry()
        internal
        returns (MockAgentIdentityRegistry registry)
    {
        address configured = _envAddressOrZero(
            "MOCK_AGENT_IDENTITY_REGISTRY_ADDRESS"
        );
        if (configured != address(0)) {
            return MockAgentIdentityRegistry(configured);
        }
        registry = new MockAgentIdentityRegistry();
    }

    function _escrowReleaser() internal returns (MockEscrowReleaser releaser) {
        address configured = _envAddressOrZero("MOCK_ESCROW_RELEASER_ADDRESS");
        if (configured != address(0)) {
            return MockEscrowReleaser(configured);
        }
        releaser = new MockEscrowReleaser();
    }

    function _envAddressOrZero(
        string memory key
    ) internal view returns (address) {
        try vm.envAddress(key) returns (address value) {
            return value;
        } catch {
            return address(0);
        }
    }
}
