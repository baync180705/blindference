// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {ReputationRegistry} from "../../contracts/core/ReputationRegistry.sol";
import {IReputationRegistry as IRR} from "../../contracts/interfaces/core/IReputationRegistry.sol";
import {IExecutionCommitmentRegistry as IECR} from "../../contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {IArbiterSelectionRegistry as IASR} from "../../contracts/interfaces/core/IArbiterSelectionRegistry.sol";
import {MockExecutionCommitmentRegistry} from "../../contracts/mocks/MockExecutionCommitmentRegistry.sol";

contract MockArbiterSelectionRegistryStub is IASR {
    Arbitration private _arb;
    mapping(uint256 => mapping(address => bytes32)) private _reveals;

    function setArbitration(Arbitration calldata a) external {
        _arb.invocationId = a.invocationId;
        _arb.arbiters = a.arbiters;
        _arb.selectedAt = a.selectedAt;
        _arb.commitDeadline = a.commitDeadline;
        _arb.revealDeadline = a.revealDeadline;
        _arb.majorityOutput = a.majorityOutput;
        _arb.majorityCount = a.majorityCount;
        _arb.status = a.status;
    }

    function setReveal(uint256 invocationId, address arbiter, bytes32 outputHandle) external {
        _reveals[invocationId][arbiter] = outputHandle;
    }

    function arbitrationOf(uint256) external view returns (Arbitration memory) {
        return _arb;
    }

    function revealOf(uint256 invocationId, address arbiter) external view returns (bytes32) {
        return _reveals[invocationId][arbiter];
    }

    function registerArbiter() external payable {
        revert("mock");
    }

    function unregisterArbiter() external pure {
        revert("mock");
    }

    function requestArbitration(uint256, uint8) external pure returns (address[] memory) {
        revert("mock");
    }

    function arbiterCommit(uint256, bytes32) external pure {
        revert("mock");
    }

    function arbiterReveal(uint256, bytes32, bytes32) external pure {
        revert("mock");
    }

    function finalize(uint256) external pure {
        revert("mock");
    }

    function commitDigest(address, bytes32, bytes32) external pure returns (bytes32) {
        return bytes32(0);
    }

    function commitOf(uint256, address) external pure returns (bytes32) {
        return bytes32(0);
    }

    function isRegistered(address) external pure returns (bool) {
        return false;
    }

    function poolSize() external pure returns (uint256) {
        return 0;
    }
}

contract ReputationRegistryTest is Test {
    ReputationRegistry public reputation;
    MockArbiterSelectionRegistryStub public asr;
    MockExecutionCommitmentRegistry public ecr;

    address public owner = makeAddr("owner");
    address public node = makeAddr("node");
    address public other = makeAddr("other");
    address public arb1 = makeAddr("arb1");
    address public arb2 = makeAddr("arb2");
    address public arb3 = makeAddr("arb3");

    uint256 public constant INVOCATION_ID = 1;
    uint64 public constant CYCLE_DURATION = 1 days;
    bytes32 public constant MAJORITY = bytes32(uint256(0xCAFE));
    bytes32 public constant LOSER = bytes32(uint256(0xBEEF));

    function setUp() public {
        asr = new MockArbiterSelectionRegistryStub();
        ecr = new MockExecutionCommitmentRegistry();

        ReputationRegistry impl = new ReputationRegistry(address(0));
        reputation = ReputationRegistry(
            address(
                new ERC1967Proxy(
                    address(impl),
                    abi.encodeCall(ReputationRegistry.initialize, (owner, address(asr), address(ecr), CYCLE_DURATION))
                )
            )
        );
    }

    function _setArbitrationWithMajority(address[] memory arbiters) internal {
        IASR.Arbitration memory a;
        a.invocationId = INVOCATION_ID;
        a.arbiters = arbiters;
        a.majorityOutput = MAJORITY;
        a.majorityCount = uint8(arbiters.length / 2 + 1);
        a.status = IASR.ArbitrationStatus.RESOLVED_MAJORITY;
        asr.setArbitration(a);
    }

    function test_recordHonestCycle_incrementsScore() public {
        skip(CYCLE_DURATION * 2);
        uint64 priorCycle = reputation.currentCycle() - 1;

        reputation.recordHonestCycle(node, priorCycle);
        IRR.Reputation memory r = reputation.reputationOf(node);
        assertEq(r.score, 1);
        assertEq(r.cyclesActive, 1);
    }

    function test_recordHonestCycle_revertsForCurrentCycle() public {
        skip(CYCLE_DURATION);
        uint64 cur = reputation.currentCycle();
        vm.expectRevert(IRR.CycleNotEnded.selector);
        reputation.recordHonestCycle(node, cur);
    }

    function test_recordHonestCycle_cannotDoubleCredit() public {
        skip(CYCLE_DURATION * 2);
        uint64 priorCycle = reputation.currentCycle() - 1;
        reputation.recordHonestCycle(node, priorCycle);
        vm.expectRevert(IRR.AlreadyCreditedThisCycle.selector);
        reputation.recordHonestCycle(node, priorCycle);
    }

    function test_recordFraudFromArbitration_arbiterMinority_resetsScore() public {
        for (uint256 i = 0; i < 5; i++) {
            skip(CYCLE_DURATION);
        }
        uint64 priorCycle = reputation.currentCycle() - 1;
        for (uint256 i = 0; i < 4; i++) {
            reputation.recordHonestCycle(node, priorCycle - uint64(i));
        }
        assertEq(reputation.reputationOf(node).score, 4);

        address[] memory arbiters = new address[](3);
        arbiters[0] = node;
        arbiters[1] = arb1;
        arbiters[2] = arb2;
        _setArbitrationWithMajority(arbiters);
        asr.setReveal(INVOCATION_ID, node, LOSER);

        reputation.recordFraudFromArbitration(INVOCATION_ID, node, IRR.FraudReason.ARBITER_MINORITY);

        IRR.Reputation memory r = reputation.reputationOf(node);
        assertEq(r.score, 0);
        assertEq(r.cyclesGuilty, 1);
        assertTrue(reputation.isGuiltyInCycle(node, reputation.currentCycle()));
    }

    function test_recordFraudFromArbitration_revertsForHonestArbiter() public {
        address[] memory arbiters = new address[](3);
        arbiters[0] = node;
        arbiters[1] = arb1;
        arbiters[2] = arb2;
        _setArbitrationWithMajority(arbiters);
        asr.setReveal(INVOCATION_ID, node, MAJORITY);

        vm.expectRevert(IRR.NodeNotOnLosingSide.selector);
        reputation.recordFraudFromArbitration(INVOCATION_ID, node, IRR.FraudReason.ARBITER_MINORITY);
    }

    function test_recordFraudFromArbitration_executorWrong_resets() public {
        IECR.Invocation memory inv;
        inv.executor = node;
        inv.crossVerifier = other;
        inv.executorOutput = LOSER;
        inv.verifierOutput = MAJORITY;
        inv.executorRevealed = true;
        inv.verifierRevealed = true;
        inv.status = IECR.Status.ESCALATED;
        ecr.setInvocation(INVOCATION_ID, 0, 0, inv.executor, inv.crossVerifier, IECR.Status.ESCALATED);

        address[] memory arbiters = new address[](3);
        arbiters[0] = arb1;
        arbiters[1] = arb2;
        arbiters[2] = arb3;
        _setArbitrationWithMajority(arbiters);

        vm.expectRevert();
        reputation.recordFraudFromArbitration(INVOCATION_ID, node, IRR.FraudReason.EXECUTOR_WRONG);
    }

    function test_recordFraudFromArbitration_revertsWhenNoMajority() public {
        IASR.Arbitration memory a;
        a.invocationId = INVOCATION_ID;
        a.status = IASR.ArbitrationStatus.TIMED_OUT;
        asr.setArbitration(a);

        vm.expectRevert(IRR.NoArbitrationMajority.selector);
        reputation.recordFraudFromArbitration(INVOCATION_ID, node, IRR.FraudReason.ARBITER_MINORITY);
    }

    function test_arbitrationFrequencyBps_decreasesWithReputation() public {
        assertEq(reputation.arbitrationFrequencyBps(node), 10_000);

        skip(CYCLE_DURATION * 11);
        for (uint64 c = 0; c < 10; c++) {
            reputation.recordHonestCycle(node, c);
        }
        assertEq(reputation.arbitrationFrequencyBps(node), 1_000);
    }

    function test_recordHonestCycle_blockedIfGuiltyInCycle() public {
        skip(CYCLE_DURATION * 2);
        uint64 cycle = reputation.currentCycle();

        address[] memory arbiters = new address[](3);
        arbiters[0] = node;
        arbiters[1] = arb1;
        arbiters[2] = arb2;
        _setArbitrationWithMajority(arbiters);
        asr.setReveal(INVOCATION_ID, node, LOSER);

        reputation.recordFraudFromArbitration(INVOCATION_ID, node, IRR.FraudReason.ARBITER_MINORITY);

        skip(CYCLE_DURATION);
        vm.expectRevert(IRR.AlreadyResetThisCycle.selector);
        reputation.recordHonestCycle(node, cycle);
    }
}
