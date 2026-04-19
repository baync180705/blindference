// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {RewardAccumulator} from "../../contracts/core/RewardAccumulator.sol";
import {ReputationRegistry} from "../../contracts/core/ReputationRegistry.sol";
import {IRewardAccumulator as IRA} from "../../contracts/interfaces/core/IRewardAccumulator.sol";
import {IReputationRegistry as IRR} from "../../contracts/interfaces/core/IReputationRegistry.sol";
import {IArbiterSelectionRegistry as IASR} from "../../contracts/interfaces/core/IArbiterSelectionRegistry.sol";
import {MockExecutionCommitmentRegistry} from "../../contracts/mocks/MockExecutionCommitmentRegistry.sol";
import {MockEscrowReleaser} from "../../contracts/mocks/MockEscrowReleaser.sol";

contract MockArbiterSelectionRegistryStub is IASR {
    Arbitration private _arb;
    mapping(uint256 => mapping(address => bytes32)) private _reveals;

    function setArbitration(Arbitration calldata a) external {
        _arb.invocationId = a.invocationId;
        _arb.arbiters = a.arbiters;
        _arb.majorityOutput = a.majorityOutput;
        _arb.majorityCount = a.majorityCount;
        _arb.status = a.status;
    }

    function setReveal(uint256 i, address a, bytes32 v) external {
        _reveals[i][a] = v;
    }

    function arbitrationOf(uint256) external view returns (Arbitration memory) {
        return _arb;
    }

    function revealOf(uint256 i, address a) external view returns (bytes32) {
        return _reveals[i][a];
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

contract RewardAccumulatorTest is Test {
    RewardAccumulator public accumulator;
    ReputationRegistry public reputation;
    MockArbiterSelectionRegistryStub public asr;
    MockExecutionCommitmentRegistry public ecr;
    MockEscrowReleaser public releaser;

    address public owner = makeAddr("owner");
    address public accruer = makeAddr("accruer");
    address public node = makeAddr("node");
    address public outsider = makeAddr("outsider");

    uint64 public constant CYCLE_DURATION = 1 days;
    uint64 public constant MIN_WORK = 2;
    uint64 public constant MIN_VALIDATION = 1;

    uint256 public constant ESCROW_ID = 9001;
    bytes32 public constant WORK_REF = bytes32(uint256(0xABCD));

    function setUp() public {
        asr = new MockArbiterSelectionRegistryStub();
        ecr = new MockExecutionCommitmentRegistry();
        releaser = new MockEscrowReleaser();

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
                        (owner, address(reputation), address(releaser), MIN_WORK, MIN_VALIDATION)
                    )
                )
            )
        );

        vm.prank(owner);
        accumulator.setAccruer(accruer, true);
    }

    function _accrue(IRA.WorkRole role, uint256 amount) internal {
        uint64 cycle = reputation.currentCycle();
        vm.prank(accruer);
        accumulator.accrue(node, cycle, ESCROW_ID, role, amount, WORK_REF);
    }

    function test_accrue_revertsForUnauthorized() public {
        vm.prank(outsider);
        vm.expectRevert(IRA.NotAuthorizedAccruer.selector);
        accumulator.accrue(node, 0, ESCROW_ID, IRA.WorkRole.EXECUTOR, 100, WORK_REF);
    }

    function test_accrue_revertsForZeroAmount() public {
        vm.prank(accruer);
        vm.expectRevert(IRA.ZeroAmount.selector);
        accumulator.accrue(node, 0, ESCROW_ID, IRA.WorkRole.EXECUTOR, 0, WORK_REF);
    }

    function test_accrue_incrementsWorkOrValidationCounts() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);
        _accrue(IRA.WorkRole.ARBITER, 25);

        uint64 cycle = reputation.currentCycle();
        assertEq(accumulator.workCount(node, cycle), 2);
        assertEq(accumulator.validationCount(node, cycle), 1);
        assertEq(accumulator.pendingTotal(node, cycle), 175);
    }

    function test_release_succeedsWhenAllCriteriaPass() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);
        _accrue(IRA.WorkRole.ARBITER, 25);

        uint64 cycle = reputation.currentCycle();
        skip(CYCLE_DURATION + 1);

        accumulator.release(node, cycle);

        assertEq(releaser.callCount(), 3);
        IRA.AccruedItem[] memory items = accumulator.pendingItems(node, cycle);
        for (uint256 i = 0; i < items.length; i++) {
            assertEq(uint8(items[i].status), uint8(IRA.ItemStatus.RELEASED));
        }
    }

    function test_release_revertsBeforeCycleEnds() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);
        _accrue(IRA.WorkRole.ARBITER, 25);

        uint64 cycle = reputation.currentCycle();
        vm.expectRevert(IRA.CycleNotEnded.selector);
        accumulator.release(node, cycle);
    }

    function test_release_failsAccuracyCriterionWhenGuilty() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);
        _accrue(IRA.WorkRole.ARBITER, 25);

        address[] memory arbiters = new address[](3);
        arbiters[0] = node;
        arbiters[1] = makeAddr("a1");
        arbiters[2] = makeAddr("a2");
        IASR.Arbitration memory a;
        a.invocationId = 1;
        a.arbiters = arbiters;
        a.majorityOutput = bytes32(uint256(0xCAFE));
        a.majorityCount = 2;
        a.status = IASR.ArbitrationStatus.RESOLVED_MAJORITY;
        asr.setArbitration(a);
        asr.setReveal(1, node, bytes32(uint256(0xBEEF)));
        reputation.recordFraudFromArbitration(1, node, IRR.FraudReason.ARBITER_MINORITY);

        uint64 cycle = reputation.currentCycle();
        skip(CYCLE_DURATION + 1);

        vm.expectRevert(IRA.AccuracyFailed.selector);
        accumulator.release(node, cycle);
    }

    function test_release_failsWorkProportionWhenInsufficient() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.ARBITER, 25);

        uint64 cycle = reputation.currentCycle();
        skip(CYCLE_DURATION + 1);

        vm.expectRevert(IRA.WorkProportionFailed.selector);
        accumulator.release(node, cycle);
    }

    function test_release_failsValidationProportionWhenZero() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);

        uint64 cycle = reputation.currentCycle();
        skip(CYCLE_DURATION + 1);

        vm.expectRevert(IRA.ValidationProportionFailed.selector);
        accumulator.release(node, cycle);
    }

    function test_release_revertsOnDoubleRelease() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);
        _accrue(IRA.WorkRole.ARBITER, 25);

        uint64 cycle = reputation.currentCycle();
        skip(CYCLE_DURATION + 1);
        accumulator.release(node, cycle);

        vm.expectRevert(IRA.AlreadyReleased.selector);
        accumulator.release(node, cycle);
    }

    function test_forfeit_marksAllItemsForfeitedAndBlocksRelease() public {
        _accrue(IRA.WorkRole.EXECUTOR, 100);
        _accrue(IRA.WorkRole.CROSS_VERIFIER, 50);
        _accrue(IRA.WorkRole.ARBITER, 25);

        uint64 cycle = reputation.currentCycle();
        vm.prank(accruer);
        accumulator.forfeit(node, cycle);

        IRA.AccruedItem[] memory items = accumulator.pendingItems(node, cycle);
        for (uint256 i = 0; i < items.length; i++) {
            assertEq(uint8(items[i].status), uint8(IRA.ItemStatus.FORFEITED));
        }

        skip(CYCLE_DURATION + 1);
        vm.expectRevert(IRA.AlreadyReleased.selector);
        accumulator.release(node, cycle);
    }

    function test_release_revertsForNoPendingItems() public {
        skip(CYCLE_DURATION + 1);
        vm.expectRevert(IRA.NoPendingItems.selector);
        accumulator.release(node, 0);
    }
}
