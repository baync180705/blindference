// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {ExecutionCommitmentRegistry} from "../../contracts/core/ExecutionCommitmentRegistry.sol";
import {ArbiterSelectionRegistry} from "../../contracts/core/ArbiterSelectionRegistry.sol";
import {ReputationRegistry} from "../../contracts/core/ReputationRegistry.sol";
import {RewardAccumulator} from "../../contracts/core/RewardAccumulator.sol";
import {PrevRandaoRandomness} from "../../contracts/core/PrevRandaoRandomness.sol";

import {IExecutionCommitmentRegistry as IECR} from "../../contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {IArbiterSelectionRegistry as IASR} from "../../contracts/interfaces/core/IArbiterSelectionRegistry.sol";
import {IReputationRegistry as IRR} from "../../contracts/interfaces/core/IReputationRegistry.sol";
import {IRewardAccumulator as IRA} from "../../contracts/interfaces/core/IRewardAccumulator.sol";

import {MockEscrowReleaser} from "../../contracts/mocks/MockEscrowReleaser.sol";

contract BlindferenceProtocolIntegrationTest is Test {
    ExecutionCommitmentRegistry public ecr;
    ArbiterSelectionRegistry public asr;
    ReputationRegistry public reputation;
    RewardAccumulator public accumulator;
    MockEscrowReleaser public escrow;
    PrevRandaoRandomness public rng;

    address public owner = makeAddr("owner");
    address public dispatcher = makeAddr("dispatcher");
    address public orchestrator = makeAddr("orchestrator");
    address public executor = makeAddr("executor");
    address public crossVerifier = makeAddr("crossVerifier");

    address[] public arbiters;

    uint256 public constant INVOCATION_ID = 42;
    uint256 public constant ESCROW_ID = 9001;
    uint256 public constant AGENT_ID = 7;

    bytes32 public constant OUT_GOOD = bytes32(uint256(0xCAFE));
    bytes32 public constant OUT_BAD = bytes32(uint256(0xBEEF));

    bytes32 public constant SALT_E = bytes32(uint256(0x11));
    bytes32 public constant SALT_V = bytes32(uint256(0x22));

    uint256 public constant ARBITER_STAKE = 1 ether;
    uint64 public constant COMMIT_WINDOW = 10 minutes;
    uint64 public constant REVEAL_WINDOW = 10 minutes;
    uint64 public constant COOLDOWN_BLOCKS = 100;
    uint64 public constant CYCLE_DURATION = 1 days;
    uint64 public constant MIN_WORK = 1;
    uint64 public constant MIN_VALIDATION = 0;

    function setUp() public {
        rng = new PrevRandaoRandomness();
        escrow = new MockEscrowReleaser();

        ExecutionCommitmentRegistry ecrImpl = new ExecutionCommitmentRegistry(address(0));
        ecr = ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(ecrImpl), abi.encodeCall(ExecutionCommitmentRegistry.initialize, (owner, dispatcher))
                )
            )
        );

        ArbiterSelectionRegistry asrImpl = new ArbiterSelectionRegistry(address(0));
        asr = ArbiterSelectionRegistry(
            address(
                new ERC1967Proxy(
                    address(asrImpl),
                    abi.encodeCall(
                        ArbiterSelectionRegistry.initialize,
                        (
                            owner,
                            address(ecr),
                            address(rng),
                            ARBITER_STAKE,
                            COMMIT_WINDOW,
                            REVEAL_WINDOW,
                            COOLDOWN_BLOCKS
                        )
                    )
                )
            )
        );

        ReputationRegistry repImpl = new ReputationRegistry(address(0));
        reputation = ReputationRegistry(
            address(
                new ERC1967Proxy(
                    address(repImpl),
                    abi.encodeCall(ReputationRegistry.initialize, (owner, address(asr), address(ecr), CYCLE_DURATION))
                )
            )
        );

        RewardAccumulator accImpl = new RewardAccumulator(address(0));
        accumulator = RewardAccumulator(
            address(
                new ERC1967Proxy(
                    address(accImpl),
                    abi.encodeCall(
                        RewardAccumulator.initialize,
                        (owner, address(reputation), address(escrow), MIN_WORK, MIN_VALIDATION)
                    )
                )
            )
        );

        vm.prank(owner);
        accumulator.setAccruer(orchestrator, true);

        for (uint256 i = 0; i < 10; i++) {
            address a = makeAddr(string.concat("arb", vm.toString(i)));
            arbiters.push(a);
            vm.deal(a, 10 ether);
            vm.prank(a);
            asr.registerArbiter{value: ARBITER_STAKE}();
        }
    }

    function _dispatch() internal {
        vm.prank(dispatcher);
        ecr.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            crossVerifier,
            uint64(block.timestamp + COMMIT_WINDOW),
            uint64(block.timestamp + COMMIT_WINDOW + REVEAL_WINDOW)
        );
    }

    function _commitAndReveal(bytes32 executorOutput, bytes32 verifierOutput) internal {
        bytes32 eDig = ecr.commitDigest(IECR.Role.EXECUTOR, executor, executorOutput, SALT_E);
        bytes32 vDig = ecr.commitDigest(IECR.Role.CROSS_VERIFIER, crossVerifier, verifierOutput, SALT_V);

        vm.prank(executor);
        ecr.commit(INVOCATION_ID, IECR.Role.EXECUTOR, eDig);
        vm.prank(crossVerifier);
        ecr.commit(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, vDig);

        vm.prank(executor);
        ecr.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, executorOutput, SALT_E);
        vm.prank(crossVerifier);
        ecr.reveal(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, verifierOutput, SALT_V);
    }

    // ------------------------------------------------------------------
    //  Happy path
    // ------------------------------------------------------------------

    function test_happyPath_dispatchToVerified() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_GOOD);

        assertEq(uint8(ecr.statusOf(INVOCATION_ID)), uint8(IECR.Status.VERIFIED));
        assertEq(ecr.verifiedOutput(INVOCATION_ID), OUT_GOOD);
    }

    function test_happyPath_accrueAndReleaseToEscrow() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_GOOD);

        uint64 cycle = reputation.currentCycle();
        bytes32 workRef = bytes32(INVOCATION_ID);

        vm.startPrank(orchestrator);
        accumulator.accrue(executor, cycle, ESCROW_ID, IRA.WorkRole.EXECUTOR, 100, workRef);
        accumulator.accrue(crossVerifier, cycle, ESCROW_ID, IRA.WorkRole.CROSS_VERIFIER, 50, workRef);
        vm.stopPrank();

        assertEq(accumulator.workCount(executor, cycle), 1);
        assertEq(accumulator.workCount(crossVerifier, cycle), 1);
        assertEq(accumulator.pendingTotal(executor, cycle), 100);
        assertEq(accumulator.pendingTotal(crossVerifier, cycle), 50);

        skip(CYCLE_DURATION + 1);

        accumulator.release(executor, cycle);
        accumulator.release(crossVerifier, cycle);

        assertEq(escrow.callCount(), 2);
        (uint256 e0, address r0, uint256 a0) = escrow.calls(0);
        (uint256 e1, address r1, uint256 a1) = escrow.calls(1);
        assertEq(e0, ESCROW_ID);
        assertEq(r0, executor);
        assertEq(a0, 100);
        assertEq(e1, ESCROW_ID);
        assertEq(r1, crossVerifier);
        assertEq(a1, 50);
    }

    // ------------------------------------------------------------------
    //  Mismatch escalation → arbitration → reputation reset
    // ------------------------------------------------------------------

    function test_mismatch_escalatesToArbitration() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_BAD);

        assertEq(uint8(ecr.statusOf(INVOCATION_ID)), uint8(IECR.Status.ESCALATED));

        address[] memory selected = asr.requestArbitration(INVOCATION_ID, 5);
        assertEq(selected.length, 5);
        for (uint256 i = 0; i < 5; i++) {
            assertTrue(selected[i] != executor && selected[i] != crossVerifier);
        }
    }

    function test_arbitration_majorityResolves_andLoserReputationResets() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_BAD);
        address[] memory selected = asr.requestArbitration(INVOCATION_ID, 5);

        bytes32[5] memory salts =
            [bytes32(uint256(1)), bytes32(uint256(2)), bytes32(uint256(3)), bytes32(uint256(4)), bytes32(uint256(5))];

        for (uint256 i = 0; i < 3; i++) {
            bytes32 d = asr.commitDigest(selected[i], OUT_GOOD, salts[i]);
            vm.prank(selected[i]);
            asr.arbiterCommit(INVOCATION_ID, d);
        }
        for (uint256 i = 3; i < 5; i++) {
            bytes32 d = asr.commitDigest(selected[i], OUT_BAD, salts[i]);
            vm.prank(selected[i]);
            asr.arbiterCommit(INVOCATION_ID, d);
        }

        skip(COMMIT_WINDOW + 1);

        for (uint256 i = 0; i < 3; i++) {
            vm.prank(selected[i]);
            asr.arbiterReveal(INVOCATION_ID, OUT_GOOD, salts[i]);
        }
        for (uint256 i = 3; i < 5; i++) {
            vm.prank(selected[i]);
            asr.arbiterReveal(INVOCATION_ID, OUT_BAD, salts[i]);
        }

        asr.finalize(INVOCATION_ID);

        IASR.Arbitration memory a = asr.arbitrationOf(INVOCATION_ID);
        assertEq(uint8(a.status), uint8(IASR.ArbitrationStatus.RESOLVED_MAJORITY));
        assertEq(a.majorityOutput, OUT_GOOD);

        reputation.recordFraudFromArbitration(INVOCATION_ID, crossVerifier, IRR.FraudReason.VERIFIER_WRONG);
        IRR.Reputation memory verifierRep = reputation.reputationOf(crossVerifier);
        assertEq(verifierRep.cyclesGuilty, 1);
        assertTrue(reputation.isGuiltyInCycle(crossVerifier, reputation.currentCycle()));

        for (uint256 i = 3; i < 5; i++) {
            reputation.recordFraudFromArbitration(INVOCATION_ID, selected[i], IRR.FraudReason.ARBITER_MINORITY);
            assertEq(reputation.reputationOf(selected[i]).cyclesGuilty, 1);
        }

        for (uint256 i = 0; i < 3; i++) {
            assertEq(reputation.reputationOf(selected[i]).cyclesGuilty, 0);
        }

        vm.expectRevert(IRR.NodeNotOnLosingSide.selector);
        reputation.recordFraudFromArbitration(INVOCATION_ID, executor, IRR.FraudReason.EXECUTOR_WRONG);
    }

    function test_arbitration_loserAccrualForfeited_winnerReleased() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_BAD);
        address[] memory selected = asr.requestArbitration(INVOCATION_ID, 5);

        bytes32[5] memory salts =
            [bytes32(uint256(1)), bytes32(uint256(2)), bytes32(uint256(3)), bytes32(uint256(4)), bytes32(uint256(5))];
        for (uint256 i = 0; i < 5; i++) {
            bytes32 out = i < 3 ? OUT_GOOD : OUT_BAD;
            bytes32 d = asr.commitDigest(selected[i], out, salts[i]);
            vm.prank(selected[i]);
            asr.arbiterCommit(INVOCATION_ID, d);
        }
        skip(COMMIT_WINDOW + 1);
        for (uint256 i = 0; i < 5; i++) {
            bytes32 out = i < 3 ? OUT_GOOD : OUT_BAD;
            vm.prank(selected[i]);
            asr.arbiterReveal(INVOCATION_ID, out, salts[i]);
        }
        asr.finalize(INVOCATION_ID);

        reputation.recordFraudFromArbitration(INVOCATION_ID, crossVerifier, IRR.FraudReason.VERIFIER_WRONG);

        uint64 cycle = reputation.currentCycle();
        bytes32 workRef = bytes32(INVOCATION_ID);

        vm.startPrank(orchestrator);
        accumulator.accrue(executor, cycle, ESCROW_ID, IRA.WorkRole.EXECUTOR, 100, workRef);
        accumulator.accrue(crossVerifier, cycle, ESCROW_ID, IRA.WorkRole.CROSS_VERIFIER, 50, workRef);
        accumulator.forfeit(crossVerifier, cycle);
        vm.stopPrank();

        skip(CYCLE_DURATION + 1);

        accumulator.release(executor, cycle);
        assertEq(escrow.callCount(), 1);

        vm.expectRevert(IRA.AlreadyReleased.selector);
        accumulator.release(crossVerifier, cycle);
    }

    // ------------------------------------------------------------------
    //  Release blockers — each Gonka criterion enforced
    // ------------------------------------------------------------------

    function test_release_blockedByAccuracyCriterion() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_BAD);
        address[] memory selected = asr.requestArbitration(INVOCATION_ID, 5);

        bytes32[5] memory salts =
            [bytes32(uint256(1)), bytes32(uint256(2)), bytes32(uint256(3)), bytes32(uint256(4)), bytes32(uint256(5))];
        for (uint256 i = 0; i < 5; i++) {
            bytes32 out = i < 3 ? OUT_GOOD : OUT_BAD;
            bytes32 d = asr.commitDigest(selected[i], out, salts[i]);
            vm.prank(selected[i]);
            asr.arbiterCommit(INVOCATION_ID, d);
        }
        skip(COMMIT_WINDOW + 1);
        for (uint256 i = 0; i < 5; i++) {
            bytes32 out = i < 3 ? OUT_GOOD : OUT_BAD;
            vm.prank(selected[i]);
            asr.arbiterReveal(INVOCATION_ID, out, salts[i]);
        }
        asr.finalize(INVOCATION_ID);

        reputation.recordFraudFromArbitration(INVOCATION_ID, crossVerifier, IRR.FraudReason.VERIFIER_WRONG);

        uint64 cycle = reputation.currentCycle();
        vm.prank(orchestrator);
        accumulator.accrue(crossVerifier, cycle, ESCROW_ID, IRA.WorkRole.CROSS_VERIFIER, 50, bytes32(0));

        skip(CYCLE_DURATION + 1);
        vm.expectRevert(IRA.AccuracyFailed.selector);
        accumulator.release(crossVerifier, cycle);
    }

    function test_release_blockedByWorkProportion() public {
        RewardAccumulator strictImpl = new RewardAccumulator(address(0));
        RewardAccumulator strict = RewardAccumulator(
            address(
                new ERC1967Proxy(
                    address(strictImpl),
                    abi.encodeCall(RewardAccumulator.initialize, (owner, address(reputation), address(escrow), 5, 0))
                )
            )
        );
        vm.prank(owner);
        strict.setAccruer(orchestrator, true);

        uint64 cycle = reputation.currentCycle();
        vm.prank(orchestrator);
        strict.accrue(executor, cycle, ESCROW_ID, IRA.WorkRole.EXECUTOR, 100, bytes32(0));

        skip(CYCLE_DURATION + 1);
        vm.expectRevert(IRA.WorkProportionFailed.selector);
        strict.release(executor, cycle);
    }

    function test_release_blockedByValidationProportion() public {
        RewardAccumulator strictImpl = new RewardAccumulator(address(0));
        RewardAccumulator strict = RewardAccumulator(
            address(
                new ERC1967Proxy(
                    address(strictImpl),
                    abi.encodeCall(RewardAccumulator.initialize, (owner, address(reputation), address(escrow), 0, 1))
                )
            )
        );
        vm.prank(owner);
        strict.setAccruer(orchestrator, true);

        uint64 cycle = reputation.currentCycle();
        vm.prank(orchestrator);
        strict.accrue(executor, cycle, ESCROW_ID, IRA.WorkRole.EXECUTOR, 100, bytes32(0));

        skip(CYCLE_DURATION + 1);
        vm.expectRevert(IRA.ValidationProportionFailed.selector);
        strict.release(executor, cycle);
    }

    // ------------------------------------------------------------------
    //  Reputation lifecycle — full cycle credit after honest work
    // ------------------------------------------------------------------

    function test_honestCycleCredit_increasesScoreAcrossLifecycle() public {
        _dispatch();
        _commitAndReveal(OUT_GOOD, OUT_GOOD);

        uint64 cycle = reputation.currentCycle();
        skip(CYCLE_DURATION + 1);

        reputation.recordHonestCycle(executor, cycle);
        reputation.recordHonestCycle(crossVerifier, cycle);

        assertEq(reputation.reputationOf(executor).score, 1);
        assertEq(reputation.reputationOf(crossVerifier).score, 1);
        assertEq(reputation.reputationOf(executor).cyclesActive, 1);
    }
}
