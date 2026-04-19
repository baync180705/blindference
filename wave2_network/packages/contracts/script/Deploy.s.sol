// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {AgentConfigRegistry} from "../contracts/core/AgentConfigRegistry.sol";
import {ArbiterSelectionRegistry} from "../contracts/core/ArbiterSelectionRegistry.sol";
import {ExecutionCommitmentRegistry} from "../contracts/core/ExecutionCommitmentRegistry.sol";
import {NodeAttestationRegistry} from "../contracts/core/NodeAttestationRegistry.sol";
import {PrevRandaoRandomness} from "../contracts/core/PrevRandaoRandomness.sol";
import {ReputationRegistry} from "../contracts/core/ReputationRegistry.sol";
import {RewardAccumulator} from "../contracts/core/RewardAccumulator.sol";
import {MockAgentIdentityRegistry} from "../contracts/mocks/MockAgentIdentityRegistry.sol";
import {MockEscrowReleaser} from "../contracts/mocks/MockEscrowReleaser.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address owner = vm.addr(deployerPrivateKey);
        address dispatcher = _envOr("ICL_SERVICE_ADDRESS", owner);

        vm.startBroadcast(deployerPrivateKey);

        MockAgentIdentityRegistry identity = new MockAgentIdentityRegistry();
        MockEscrowReleaser escrowReleaser = new MockEscrowReleaser();
        PrevRandaoRandomness randomness = new PrevRandaoRandomness();

        ExecutionCommitmentRegistry execution = _deployExecution(owner, dispatcher);
        ArbiterSelectionRegistry arbiter = _deployArbiter(owner, execution, randomness);
        ReputationRegistry reputation = _deployReputation(owner, arbiter, execution);
        RewardAccumulator rewardAccumulator = _deployRewardAccumulator(owner, dispatcher, reputation, escrowReleaser);
        NodeAttestationRegistry nodeAttestation = _deployNodeAttestation(owner);
        AgentConfigRegistry agentConfig = _deployAgentConfig(owner, identity);

        identity.register(1, owner);
        identity.register(2, owner);

        vm.stopBroadcast();

        console2.log("NODE_ATTESTATION_REGISTRY_ADDRESS=", address(nodeAttestation));
        console2.log("EXECUTION_COMMITMENT_REGISTRY_ADDRESS=", address(execution));
        console2.log("AGENT_CONFIG_REGISTRY_ADDRESS=", address(agentConfig));
        console2.log("REPUTATION_REGISTRY_ADDRESS=", address(reputation));
        console2.log("REWARD_ACCUMULATOR_ADDRESS=", address(rewardAccumulator));
        console2.log("ARBITER_SELECTION_REGISTRY_ADDRESS=", address(arbiter));
        console2.log("MOCK_AGENT_IDENTITY_REGISTRY_ADDRESS=", address(identity));
        console2.log("MOCK_ESCROW_RELEASER_ADDRESS=", address(escrowReleaser));
        console2.log("PREVRANDAO_RANDOMNESS_ADDRESS=", address(randomness));
    }

    function _deployExecution(address owner, address dispatcher) private returns (ExecutionCommitmentRegistry) {
        ExecutionCommitmentRegistry implementation = new ExecutionCommitmentRegistry(address(0));
        return ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(ExecutionCommitmentRegistry.initialize, (owner, dispatcher))
                )
            )
        );
    }

    function _deployArbiter(
        address owner,
        ExecutionCommitmentRegistry execution,
        PrevRandaoRandomness randomness
    ) private returns (ArbiterSelectionRegistry) {
        ArbiterSelectionRegistry implementation = new ArbiterSelectionRegistry(address(0));
        return ArbiterSelectionRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(
                        ArbiterSelectionRegistry.initialize,
                        (owner, address(execution), address(randomness), 1 ether, 10 minutes, 10 minutes, 100)
                    )
                )
            )
        );
    }

    function _deployReputation(
        address owner,
        ArbiterSelectionRegistry arbiter,
        ExecutionCommitmentRegistry execution
    ) private returns (ReputationRegistry) {
        ReputationRegistry implementation = new ReputationRegistry(address(0));
        return ReputationRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(ReputationRegistry.initialize, (owner, address(arbiter), address(execution), 1 days))
                )
            )
        );
    }

    function _deployRewardAccumulator(
        address owner,
        address dispatcher,
        ReputationRegistry reputation,
        MockEscrowReleaser escrowReleaser
    ) private returns (RewardAccumulator rewardAccumulator) {
        RewardAccumulator implementation = new RewardAccumulator(address(0));
        rewardAccumulator = RewardAccumulator(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(
                        RewardAccumulator.initialize,
                        (owner, address(reputation), address(escrowReleaser), 1, 0)
                    )
                )
            )
        );
        rewardAccumulator.setAccruer(dispatcher, true);
    }

    function _deployNodeAttestation(address owner) private returns (NodeAttestationRegistry) {
        NodeAttestationRegistry implementation = new NodeAttestationRegistry(address(0));
        return NodeAttestationRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(NodeAttestationRegistry.initialize, (owner))
                )
            )
        );
    }

    function _deployAgentConfig(address owner, MockAgentIdentityRegistry identity)
        private
        returns (AgentConfigRegistry)
    {
        AgentConfigRegistry implementation = new AgentConfigRegistry(address(0));
        return AgentConfigRegistry(
            address(
                new ERC1967Proxy(
                    address(implementation),
                    abi.encodeCall(AgentConfigRegistry.initialize, (owner, address(identity)))
                )
            )
        );
    }

    function _envOr(string memory key, address fallbackValue) private view returns (address) {
        try vm.envAddress(key) returns (address value) {
            return value;
        } catch {
            return fallbackValue;
        }
    }
}
