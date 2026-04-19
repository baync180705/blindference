// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {ArbiterSelectionRegistry} from "../../contracts/core/ArbiterSelectionRegistry.sol";
import {IArbiterSelectionRegistry as IASR} from "../../contracts/interfaces/core/IArbiterSelectionRegistry.sol";
import {IExecutionCommitmentRegistry as IECR} from "../../contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {MockExecutionCommitmentRegistry} from "../../contracts/mocks/MockExecutionCommitmentRegistry.sol";
import {MockRandomnessProvider} from "../../contracts/mocks/MockRandomnessProvider.sol";

contract ArbiterSelectionRegistryTest is Test {
    ArbiterSelectionRegistry public asr;
    MockExecutionCommitmentRegistry public ecr;
    MockRandomnessProvider public rng;

    address public owner = makeAddr("owner");
    address public executor = makeAddr("executor");
    address public crossVerifier = makeAddr("crossVerifier");

    address[] public arbiters;

    uint256 public constant MIN_STAKE = 1 ether;
    uint64 public constant COMMIT_WINDOW = 10 minutes;
    uint64 public constant REVEAL_WINDOW = 10 minutes;
    uint64 public constant COOLDOWN_BLOCKS = 100;

    uint256 public constant INVOCATION_ID = 42;
    uint256 public constant ESCROW_ID = 9001;
    uint256 public constant AGENT_ID = 7;

    bytes32 public constant OUT_TRUE = bytes32(uint256(0xCAFE));
    bytes32 public constant OUT_FALSE = bytes32(uint256(0xBEEF));

    function setUp() public {
        ecr = new MockExecutionCommitmentRegistry();
        rng = new MockRandomnessProvider();

        ArbiterSelectionRegistry impl = new ArbiterSelectionRegistry(address(0));
        asr = ArbiterSelectionRegistry(
            address(
                new ERC1967Proxy(
                    address(impl),
                    abi.encodeCall(
                        ArbiterSelectionRegistry.initialize,
                        (owner, address(ecr), address(rng), MIN_STAKE, COMMIT_WINDOW, REVEAL_WINDOW, COOLDOWN_BLOCKS)
                    )
                )
            )
        );

        for (uint256 i = 0; i < 10; i++) {
            address a = makeAddr(string.concat("arb", vm.toString(i)));
            arbiters.push(a);
            vm.deal(a, 10 ether);
            vm.prank(a);
            asr.registerArbiter{value: MIN_STAKE}();
        }

        ecr.setInvocation(INVOCATION_ID, ESCROW_ID, AGENT_ID, executor, crossVerifier, IECR.Status.ESCALATED);
    }

    function _selectFive() internal returns (address[] memory) {
        return asr.requestArbitration(INVOCATION_ID, 5);
    }

    function _digest(address arbiter, bytes32 output, bytes32 salt) internal view returns (bytes32) {
        return asr.commitDigest(arbiter, output, salt);
    }

    function test_register_addsToPoolAndStoresStake() public {
        assertEq(asr.poolSize(), 10);
        assertTrue(asr.isRegistered(arbiters[0]));
    }

    function test_register_revertsOnInsufficientStake() public {
        address newbie = makeAddr("newbie");
        vm.deal(newbie, 1 ether);
        vm.prank(newbie);
        vm.expectRevert(IASR.InsufficientStake.selector);
        asr.registerArbiter{value: 0.5 ether}();
    }

    function test_register_revertsOnDoubleRegister() public {
        vm.prank(arbiters[0]);
        vm.expectRevert(IASR.AlreadyRegistered.selector);
        asr.registerArbiter{value: MIN_STAKE}();
    }

    function test_unregister_returnsStakeAndRemovesFromPool() public {
        uint256 sizeBefore = asr.poolSize();
        uint256 balBefore = arbiters[0].balance;

        vm.prank(arbiters[0]);
        asr.unregisterArbiter();

        assertEq(asr.poolSize(), sizeBefore - 1);
        assertFalse(asr.isRegistered(arbiters[0]));
        assertEq(arbiters[0].balance, balBefore + MIN_STAKE);
    }

    function test_requestArbitration_picksFiveDistinctArbiters() public {
        address[] memory selected = _selectFive();
        assertEq(selected.length, 5);

        for (uint256 i = 0; i < 5; i++) {
            for (uint256 j = i + 1; j < 5; j++) {
                assertTrue(selected[i] != selected[j], "arbiters must be distinct");
            }
            assertTrue(asr.isRegistered(selected[i]));
            assertTrue(selected[i] != executor);
            assertTrue(selected[i] != crossVerifier);
        }
    }

    function test_requestArbitration_revertsForEvenK() public {
        vm.expectRevert(IASR.InvalidK.selector);
        asr.requestArbitration(INVOCATION_ID, 4);
    }

    function test_requestArbitration_revertsForZeroK() public {
        vm.expectRevert(IASR.InvalidK.selector);
        asr.requestArbitration(INVOCATION_ID, 0);
    }

    function test_requestArbitration_revertsWhenInvocationNotEscalated() public {
        ecr.setInvocation(999, 0, 0, executor, crossVerifier, IECR.Status.VERIFIED);
        vm.expectRevert(IASR.InvocationNotEscalated.selector);
        asr.requestArbitration(999, 5);
    }

    function test_requestArbitration_revertsOnDoubleRequest() public {
        _selectFive();
        vm.expectRevert(IASR.AlreadyArbitrating.selector);
        asr.requestArbitration(INVOCATION_ID, 5);
    }

    function test_requestArbitration_revertsWhenPoolTooSmall() public {
        for (uint256 i = 0; i < 10; i++) {
            vm.prank(arbiters[i]);
            asr.unregisterArbiter();
        }
        ecr.setInvocation(123, ESCROW_ID, AGENT_ID, executor, crossVerifier, IECR.Status.ESCALATED);
        vm.expectRevert(IASR.PoolTooSmall.selector);
        asr.requestArbitration(123, 5);
    }

    function test_cooldown_excludesArbitersWhoRecentlyArbitratedSameSubject() public {
        for (uint256 i = 0; i < 4; i++) {
            vm.prank(arbiters[i + 6]);
            asr.unregisterArbiter();
        }
        assertEq(asr.poolSize(), 6);

        _selectFive();
        ecr.setInvocation(INVOCATION_ID + 1, ESCROW_ID, AGENT_ID, executor, crossVerifier, IECR.Status.ESCALATED);

        vm.expectRevert(IASR.PoolTooSmall.selector);
        asr.requestArbitration(INVOCATION_ID + 1, 5);

        vm.roll(block.number + COOLDOWN_BLOCKS + 1);
        address[] memory secondSelection = asr.requestArbitration(INVOCATION_ID + 1, 5);
        assertEq(secondSelection.length, 5);
    }

    function _commitAndReveal(address arbiter, bytes32 output, bytes32 salt) internal {
        bytes32 d = _digest(arbiter, output, salt);
        vm.prank(arbiter);
        asr.arbiterCommit(INVOCATION_ID, d);
    }

    function test_commitReveal_majorityResolves() public {
        address[] memory selected = _selectFive();
        bytes32[5] memory salts =
            [bytes32(uint256(1)), bytes32(uint256(2)), bytes32(uint256(3)), bytes32(uint256(4)), bytes32(uint256(5))];

        _commitAndReveal(selected[0], OUT_TRUE, salts[0]);
        _commitAndReveal(selected[1], OUT_TRUE, salts[1]);
        _commitAndReveal(selected[2], OUT_TRUE, salts[2]);
        _commitAndReveal(selected[3], OUT_FALSE, salts[3]);
        _commitAndReveal(selected[4], OUT_FALSE, salts[4]);

        skip(COMMIT_WINDOW + 1);

        for (uint256 i = 0; i < 3; i++) {
            vm.prank(selected[i]);
            asr.arbiterReveal(INVOCATION_ID, OUT_TRUE, salts[i]);
        }
        for (uint256 i = 3; i < 5; i++) {
            vm.prank(selected[i]);
            asr.arbiterReveal(INVOCATION_ID, OUT_FALSE, salts[i]);
        }

        vm.expectEmit(true, false, false, true);
        emit IASR.ArbitrationResolved(INVOCATION_ID, OUT_TRUE, 3);
        asr.finalize(INVOCATION_ID);

        IASR.Arbitration memory a = asr.arbitrationOf(INVOCATION_ID);
        assertEq(uint8(a.status), uint8(IASR.ArbitrationStatus.RESOLVED_MAJORITY));
        assertEq(a.majorityOutput, OUT_TRUE);
        assertEq(a.majorityCount, 3);
    }

    function test_commit_revertsForOutsider() public {
        _selectFive();
        address outsider = makeAddr("outsider");
        vm.deal(outsider, 10 ether);
        vm.prank(outsider);
        asr.registerArbiter{value: MIN_STAKE}();

        vm.prank(outsider);
        vm.expectRevert(IASR.NotAnArbiter.selector);
        asr.arbiterCommit(INVOCATION_ID, bytes32(uint256(0xDEAD)));
    }

    function test_reveal_revertsBeforeCommitDeadline() public {
        address[] memory selected = _selectFive();
        bytes32 salt = bytes32(uint256(1));
        _commitAndReveal(selected[0], OUT_TRUE, salt);

        vm.prank(selected[0]);
        vm.expectRevert(IASR.CommitDeadlineNotPassed.selector);
        asr.arbiterReveal(INVOCATION_ID, OUT_TRUE, salt);
    }

    function test_reveal_revertsOnForgedSalt() public {
        address[] memory selected = _selectFive();
        bytes32 salt = bytes32(uint256(1));
        _commitAndReveal(selected[0], OUT_TRUE, salt);
        skip(COMMIT_WINDOW + 1);

        vm.prank(selected[0]);
        vm.expectRevert(IASR.RevealMismatch.selector);
        asr.arbiterReveal(INVOCATION_ID, OUT_TRUE, bytes32(uint256(0xFFFF)));
    }

    function test_finalize_timesOutWhenNoMajority() public {
        address[] memory selected = _selectFive();
        bytes32[5] memory salts =
            [bytes32(uint256(1)), bytes32(uint256(2)), bytes32(uint256(3)), bytes32(uint256(4)), bytes32(uint256(5))];
        bytes32 outA = bytes32(uint256(0xA));
        bytes32 outB = bytes32(uint256(0xB));
        bytes32 outC = bytes32(uint256(0xC));

        _commitAndReveal(selected[0], outA, salts[0]);
        _commitAndReveal(selected[1], outA, salts[1]);
        _commitAndReveal(selected[2], outB, salts[2]);
        _commitAndReveal(selected[3], outB, salts[3]);
        _commitAndReveal(selected[4], outC, salts[4]);

        skip(COMMIT_WINDOW + 1);

        vm.prank(selected[0]);
        asr.arbiterReveal(INVOCATION_ID, outA, salts[0]);
        vm.prank(selected[1]);
        asr.arbiterReveal(INVOCATION_ID, outA, salts[1]);
        vm.prank(selected[2]);
        asr.arbiterReveal(INVOCATION_ID, outB, salts[2]);
        vm.prank(selected[3]);
        asr.arbiterReveal(INVOCATION_ID, outB, salts[3]);
        vm.prank(selected[4]);
        asr.arbiterReveal(INVOCATION_ID, outC, salts[4]);

        skip(REVEAL_WINDOW + 1);

        vm.expectEmit(true, false, false, false);
        emit IASR.ArbitrationTimedOut(INVOCATION_ID);
        asr.finalize(INVOCATION_ID);

        IASR.Arbitration memory a = asr.arbitrationOf(INVOCATION_ID);
        assertEq(uint8(a.status), uint8(IASR.ArbitrationStatus.TIMED_OUT));
    }

    function test_commitDigest_isDeterministic() public view {
        bytes32 expected = keccak256(abi.encodePacked(arbiters[0], OUT_TRUE, bytes32(uint256(1))));
        assertEq(_digest(arbiters[0], OUT_TRUE, bytes32(uint256(1))), expected);
    }
}
