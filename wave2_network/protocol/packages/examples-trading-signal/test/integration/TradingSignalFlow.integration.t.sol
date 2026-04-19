// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {ExecutionCommitmentRegistry} from "@blindference/contracts/core/ExecutionCommitmentRegistry.sol";
import {
    IExecutionCommitmentRegistry as IECR
} from "@blindference/contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {MockEscrowReleaser} from "@blindference/contracts/mocks/MockEscrowReleaser.sol";

import {TradingSignalAttestor} from "../../contracts/core/TradingSignalAttestor.sol";
import {TradingLossUnderwriter} from "../../contracts/core/TradingLossUnderwriter.sol";
import {ITradingSignalAttestor as ITSA} from "../../contracts/interfaces/core/ITradingSignalAttestor.sol";
import {ITradingLossUnderwriter as ITLU} from "../../contracts/interfaces/core/ITradingLossUnderwriter.sol";
import {MockPriceOracle} from "../../contracts/mocks/MockPriceOracle.sol";

/// @notice End-to-end test of the insured Trading Signal Agent flow:
///
///   1. Blindference quorum (executor + cross-verifier) signs a BUY signal
///      via ExecutionCommitmentRegistry.
///   2. Agent commits the signal payload to TradingSignalAttestor; the contract
///      verifies the signal hash matches what the quorum committed to.
///   3. A trader buys loss coverage via TradingLossUnderwriter.
///   4. Time passes, price moves against the signal direction.
///   5. Trader claims; underwriter computes loss vs. configured threshold and
///      releases payout via Reineira's IEscrow seam (mocked here).
contract TradingSignalFlowIntegrationTest is Test {
    ExecutionCommitmentRegistry public ecr;
    TradingSignalAttestor public signalRegistry;
    TradingLossUnderwriter public underwriter;
    MockPriceOracle public oracle;
    MockEscrowReleaser public escrow;

    address public owner = makeAddr("owner");
    address public dispatcher = makeAddr("dispatcher");
    address public agent = makeAddr("agent");
    address public executor = makeAddr("executor");
    address public crossVerifier = makeAddr("crossVerifier");
    address public trader = makeAddr("trader");

    uint256 public constant INVOCATION_ID = 1001;
    uint256 public constant ESCROW_ID = 9001;
    uint256 public constant AGENT_ID = 7;

    bytes32 public constant ASSET = keccak256("ETH/USDC");
    int256 public constant PRICE_AT_ISSUE = 2_500e8; // $2,500
    uint16 public constant CONFIDENCE = 8_500; // 85%
    uint64 public constant SIGNAL_VALIDITY = 6 hours;

    bytes32 public constant SALT_E = bytes32(uint256(0x11));
    bytes32 public constant SALT_V = bytes32(uint256(0x22));

    uint256 public constant LOSS_THRESHOLD_BPS = 200; // 2%
    uint256 public constant HOLD_TOLERANCE_BPS = 100; // 1%
    uint256 public constant COVERAGE_AMOUNT = 1_000e6; // $1,000

    function setUp() public {
        ExecutionCommitmentRegistry ecrImpl = new ExecutionCommitmentRegistry(address(0));
        ecr = ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(ecrImpl), abi.encodeCall(ExecutionCommitmentRegistry.initialize, (owner, dispatcher))
                )
            )
        );

        TradingSignalAttestor sigImpl = new TradingSignalAttestor(address(0));
        signalRegistry = TradingSignalAttestor(
            address(
                new ERC1967Proxy(
                    address(sigImpl), abi.encodeCall(TradingSignalAttestor.initialize, (owner, address(ecr)))
                )
            )
        );

        oracle = new MockPriceOracle();
        escrow = new MockEscrowReleaser();

        TradingLossUnderwriter uwImpl = new TradingLossUnderwriter(address(0));
        underwriter = TradingLossUnderwriter(
            address(
                new ERC1967Proxy(
                    address(uwImpl),
                    abi.encodeCall(
                        TradingLossUnderwriter.initialize,
                        (
                            owner,
                            address(signalRegistry),
                            address(oracle),
                            address(escrow),
                            LOSS_THRESHOLD_BPS,
                            HOLD_TOLERANCE_BPS
                        )
                    )
                )
            )
        );
    }

    function _verifySignalThroughBlindference(bytes32 signalHash, uint64 commitDeadline, uint64 revealDeadline)
        internal
    {
        vm.prank(dispatcher);
        ecr.dispatch(INVOCATION_ID, ESCROW_ID, AGENT_ID, executor, crossVerifier, commitDeadline, revealDeadline);

        bytes32 eDigest = ecr.commitDigest(IECR.Role.EXECUTOR, executor, signalHash, SALT_E);
        bytes32 vDigest = ecr.commitDigest(IECR.Role.CROSS_VERIFIER, crossVerifier, signalHash, SALT_V);

        vm.prank(executor);
        ecr.commit(INVOCATION_ID, IECR.Role.EXECUTOR, eDigest);
        vm.prank(crossVerifier);
        ecr.commit(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, vDigest);

        vm.prank(executor);
        ecr.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, signalHash, SALT_E);
        vm.prank(crossVerifier);
        ecr.reveal(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, signalHash, SALT_V);
    }

    function _commitBuySignal() internal returns (uint64 validUntil) {
        validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);
        bytes32 signalHash =
            signalRegistry.signalDigest(ASSET, ITSA.Direction.BUY, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent);

        _verifySignalThroughBlindference(
            signalHash, uint64(block.timestamp + 5 minutes), uint64(block.timestamp + 10 minutes)
        );

        signalRegistry.commitSignal(
            INVOCATION_ID, ASSET, ITSA.Direction.BUY, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent
        );
    }

    // ------------------------------------------------------------------
    //  Happy path — bad BUY signal triggers payout
    // ------------------------------------------------------------------

    function test_endToEnd_buySignalLossTriggersPayout() public {
        uint64 validUntil = _commitBuySignal();

        ITSA.Signal memory stored = signalRegistry.signalOf(INVOCATION_ID);
        assertEq(uint8(stored.direction), uint8(ITSA.Direction.BUY));
        assertEq(stored.priceAtIssue, PRICE_AT_ISSUE);

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        ITLU.Coverage memory cov = underwriter.coverageOf(INVOCATION_ID, trader);
        assertEq(cov.coverageAmount, COVERAGE_AMOUNT);
        assertEq(cov.buyer, trader);

        // Skip past validity, then move price down 5% (BUY signal was wrong)
        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 95) / 100);

        vm.expectEmit(true, true, false, false);
        emit ITLU.ClaimPaid(INVOCATION_ID, trader, 0, 0, 0);
        vm.prank(trader);
        underwriter.claimLoss(INVOCATION_ID);

        assertEq(escrow.callCount(), 1);
        (uint256 e0, address r0, uint256 a0) = escrow.calls(0);
        assertEq(e0, ESCROW_ID);
        assertEq(r0, trader);
        assertEq(a0, (COVERAGE_AMOUNT * 500) / 10_000); // 5% loss → 5% of coverage
    }

    function test_buySignal_priceUp_noPayout() public {
        uint64 validUntil = _commitBuySignal();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 110) / 100);

        vm.prank(trader);
        vm.expectRevert();
        underwriter.claimLoss(INVOCATION_ID);
    }

    function test_buySignal_smallLossBelowThreshold_noPayout() public {
        uint64 validUntil = _commitBuySignal();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 999) / 1000); // 0.1% drop, below 2% threshold

        vm.prank(trader);
        vm.expectRevert();
        underwriter.claimLoss(INVOCATION_ID);
    }

    // ------------------------------------------------------------------
    //  SELL signal — symmetric flow
    // ------------------------------------------------------------------

    function test_sellSignal_priceUp_triggersPayout() public {
        uint64 validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);
        bytes32 signalHash =
            signalRegistry.signalDigest(ASSET, ITSA.Direction.SELL, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent);
        _verifySignalThroughBlindference(
            signalHash, uint64(block.timestamp + 5 minutes), uint64(block.timestamp + 10 minutes)
        );
        signalRegistry.commitSignal(
            INVOCATION_ID, ASSET, ITSA.Direction.SELL, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent
        );

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 110) / 100); // 10% rise — bad SELL

        vm.prank(trader);
        underwriter.claimLoss(INVOCATION_ID);

        assertEq(escrow.callCount(), 1);
        (,, uint256 a0) = escrow.calls(0);
        assertEq(a0, (COVERAGE_AMOUNT * 1000) / 10_000); // 10% loss
    }

    // ------------------------------------------------------------------
    //  Tamper resistance — signal hash mismatch
    // ------------------------------------------------------------------

    function test_commitSignal_revertsWhenAgentTampersWithDirection() public {
        uint64 validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);
        bytes32 buyHash =
            signalRegistry.signalDigest(ASSET, ITSA.Direction.BUY, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent);

        _verifySignalThroughBlindference(
            buyHash, uint64(block.timestamp + 5 minutes), uint64(block.timestamp + 10 minutes)
        );

        // Quorum signed BUY, agent tries to commit SELL → hash mismatch.
        vm.expectRevert(ITSA.SignalHashMismatch.selector);
        signalRegistry.commitSignal(
            INVOCATION_ID, ASSET, ITSA.Direction.SELL, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent
        );
    }

    function test_commitSignal_revertsWhenInvocationNotVerified() public {
        uint64 validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);

        // Skip Blindference verification entirely → ECR status is NONE.
        vm.expectRevert(ITSA.InvocationNotVerified.selector);
        signalRegistry.commitSignal(
            INVOCATION_ID, ASSET, ITSA.Direction.BUY, CONFIDENCE, PRICE_AT_ISSUE, validUntil, agent
        );
    }

    // ------------------------------------------------------------------
    //  Coverage purchase guards
    // ------------------------------------------------------------------

    function test_purchaseCoverage_revertsForUnknownSignal() public {
        vm.expectRevert(ITSA.UnknownSignal.selector);
        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);
    }

    function test_claimLoss_revertsBeforeSignalMaturity() public {
        _commitBuySignal();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 90) / 100);

        vm.prank(trader);
        vm.expectRevert(ITLU.SignalNotMature.selector);
        underwriter.claimLoss(INVOCATION_ID);
    }

    function test_claimLoss_doubleClaimReverts() public {
        uint64 validUntil = _commitBuySignal();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 90) / 100); // 10% drop

        vm.prank(trader);
        underwriter.claimLoss(INVOCATION_ID);

        vm.prank(trader);
        vm.expectRevert(ITLU.AlreadyClaimed.selector);
        underwriter.claimLoss(INVOCATION_ID);
    }
}
