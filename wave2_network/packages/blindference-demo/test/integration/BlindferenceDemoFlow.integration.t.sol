// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {ExecutionCommitmentRegistry} from "@blindference/contracts/core/ExecutionCommitmentRegistry.sol";
import {
    IExecutionCommitmentRegistry as IECR
} from "@blindference/contracts/interfaces/core/IExecutionCommitmentRegistry.sol";
import {MockEscrowReleaser} from "@blindference/contracts/mocks/MockEscrowReleaser.sol";

import {BlindferenceAttestor} from "../../contracts/core/BlindferenceAttestor.sol";
import {BlindferenceUnderwriter} from "../../contracts/core/BlindferenceUnderwriter.sol";
import {IBlindferenceAttestor as IBA} from "../../contracts/interfaces/core/IBlindferenceAttestor.sol";
import {IBlindferenceUnderwriter as IBU} from "../../contracts/interfaces/core/IBlindferenceUnderwriter.sol";
import {MockPriceOracle} from "../../contracts/mocks/MockPriceOracle.sol";

contract BlindferenceDemoFlowIntegrationTest is Test {
    ExecutionCommitmentRegistry public ecr;
    BlindferenceAttestor public attestor;
    BlindferenceUnderwriter public underwriter;
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
    bytes32 public constant MODEL_KEY = keccak256("groq:llama3-70b");
    bytes32 public constant RAW_RESPONSE_HASH = keccak256("BUY ETH/USDC WITH 85% CONFIDENCE");
    int256 public constant PRICE_AT_ISSUE = 2_500e8;
    uint16 public constant CONFIDENCE = 8_500;
    uint64 public constant SIGNAL_VALIDITY = 6 hours;

    bytes32 public constant SALT_E = bytes32(uint256(0x11));
    bytes32 public constant SALT_V = bytes32(uint256(0x22));

    uint256 public constant LOSS_THRESHOLD_BPS = 200;
    uint256 public constant HOLD_TOLERANCE_BPS = 100;
    uint256 public constant COVERAGE_AMOUNT = 1_000e6;

    function setUp() public {
        ExecutionCommitmentRegistry ecrImpl = new ExecutionCommitmentRegistry(address(0));
        ecr = ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(ecrImpl), abi.encodeCall(ExecutionCommitmentRegistry.initialize, (owner, dispatcher))
                )
            )
        );

        BlindferenceAttestor attestorImpl = new BlindferenceAttestor(address(0));
        attestor = BlindferenceAttestor(
            address(
                new ERC1967Proxy(
                    address(attestorImpl), abi.encodeCall(BlindferenceAttestor.initialize, (owner, address(ecr)))
                )
            )
        );

        oracle = new MockPriceOracle();
        escrow = new MockEscrowReleaser();

        BlindferenceUnderwriter underwriterImpl = new BlindferenceUnderwriter(address(0));
        underwriter = BlindferenceUnderwriter(
            address(
                new ERC1967Proxy(
                    address(underwriterImpl),
                    abi.encodeCall(
                        BlindferenceUnderwriter.initialize,
                        (owner, address(attestor), address(oracle), address(escrow), LOSS_THRESHOLD_BPS, HOLD_TOLERANCE_BPS)
                    )
                )
            )
        );
    }

    function _verifyOutput(bytes32 outputDigest, uint64 commitDeadline, uint64 revealDeadline) internal {
        vm.prank(dispatcher);
        ecr.dispatch(INVOCATION_ID, ESCROW_ID, AGENT_ID, executor, crossVerifier, commitDeadline, revealDeadline);

        bytes32 eDigest = ecr.commitDigest(IECR.Role.EXECUTOR, executor, outputDigest, SALT_E);
        bytes32 vDigest = ecr.commitDigest(IECR.Role.CROSS_VERIFIER, crossVerifier, outputDigest, SALT_V);

        vm.prank(executor);
        ecr.commit(INVOCATION_ID, IECR.Role.EXECUTOR, eDigest);
        vm.prank(crossVerifier);
        ecr.commit(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, vDigest);

        vm.prank(executor);
        ecr.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, outputDigest, SALT_E);
        vm.prank(crossVerifier);
        ecr.reveal(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, outputDigest, SALT_V);
    }

    function _commitBuyOutput() internal returns (uint64 validUntil, bytes32 responseHash) {
        validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);
        responseHash = RAW_RESPONSE_HASH;
        bytes32 digest = attestor.outputDigest(
            responseHash,
            ASSET,
            IBA.Recommendation.BUY,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            MODEL_KEY
        );

        _verifyOutput(digest, uint64(block.timestamp + 5 minutes), uint64(block.timestamp + 10 minutes));

        attestor.commitInferenceOutput(
            INVOCATION_ID,
            ASSET,
            IBA.Recommendation.BUY,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            responseHash,
            MODEL_KEY
        );
    }

    function test_endToEnd_buyOutputLossTriggersPayout() public {
        uint64 validUntil;
        bytes32 responseHash;
        (validUntil, responseHash) = _commitBuyOutput();

        IBA.InferenceOutput memory stored = attestor.outputOf(INVOCATION_ID);
        assertEq(uint8(stored.recommendation), uint8(IBA.Recommendation.BUY));
        assertEq(stored.priceAtIssue, PRICE_AT_ISSUE);
        assertEq(stored.responseHash, responseHash);

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        IBU.Coverage memory coverage = underwriter.coverageOf(INVOCATION_ID, trader);
        assertEq(coverage.coverageAmount, COVERAGE_AMOUNT);
        assertEq(coverage.buyer, trader);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 95) / 100);

        vm.expectEmit(true, true, false, false);
        emit IBU.ClaimPaid(INVOCATION_ID, trader, 0, 0, 0);
        vm.prank(trader);
        underwriter.claimLoss(INVOCATION_ID);

        assertEq(escrow.callCount(), 1);
        (uint256 escrowId, address recipient, uint256 payout) = escrow.calls(0);
        assertEq(escrowId, ESCROW_ID);
        assertEq(recipient, trader);
        assertEq(payout, (COVERAGE_AMOUNT * 500) / 10_000);
    }

    function test_buyOutput_priceUp_noPayout() public {
        (uint64 validUntil,) = _commitBuyOutput();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 110) / 100);

        vm.prank(trader);
        vm.expectRevert();
        underwriter.claimLoss(INVOCATION_ID);
    }

    function test_buyOutput_smallLossBelowThreshold_noPayout() public {
        (uint64 validUntil,) = _commitBuyOutput();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 999) / 1000);

        vm.prank(trader);
        vm.expectRevert();
        underwriter.claimLoss(INVOCATION_ID);
    }

    function test_sellOutput_priceUp_triggersPayout() public {
        uint64 validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);
        bytes32 digest = attestor.outputDigest(
            RAW_RESPONSE_HASH,
            ASSET,
            IBA.Recommendation.SELL,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            MODEL_KEY
        );
        _verifyOutput(digest, uint64(block.timestamp + 5 minutes), uint64(block.timestamp + 10 minutes));
        attestor.commitInferenceOutput(
            INVOCATION_ID,
            ASSET,
            IBA.Recommendation.SELL,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            RAW_RESPONSE_HASH,
            MODEL_KEY
        );

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 110) / 100);

        vm.prank(trader);
        underwriter.claimLoss(INVOCATION_ID);

        assertEq(escrow.callCount(), 1);
        (,, uint256 payout) = escrow.calls(0);
        assertEq(payout, (COVERAGE_AMOUNT * 1000) / 10_000);
    }

    function test_commitInferenceOutput_revertsWhenResponseHashIsWrong() public {
        uint64 validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);
        bytes32 digest = attestor.outputDigest(
            RAW_RESPONSE_HASH,
            ASSET,
            IBA.Recommendation.BUY,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            MODEL_KEY
        );

        _verifyOutput(digest, uint64(block.timestamp + 5 minutes), uint64(block.timestamp + 10 minutes));

        vm.expectRevert(IBA.ResponseHashMismatch.selector);
        attestor.commitInferenceOutput(
            INVOCATION_ID,
            ASSET,
            IBA.Recommendation.BUY,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            keccak256("tampered"),
            MODEL_KEY
        );
    }

    function test_commitInferenceOutput_revertsWhenInvocationNotVerified() public {
        uint64 validUntil = uint64(block.timestamp + SIGNAL_VALIDITY);

        vm.expectRevert(IBA.InvocationNotVerified.selector);
        attestor.commitInferenceOutput(
            INVOCATION_ID,
            ASSET,
            IBA.Recommendation.BUY,
            CONFIDENCE,
            PRICE_AT_ISSUE,
            validUntil,
            agent,
            RAW_RESPONSE_HASH,
            MODEL_KEY
        );
    }

    function test_purchaseCoverage_revertsForUnknownOutput() public {
        vm.expectRevert(IBA.UnknownOutput.selector);
        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);
    }

    function test_claimLoss_revertsBeforeOutputMaturity() public {
        _commitBuyOutput();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 90) / 100);

        vm.prank(trader);
        vm.expectRevert(IBU.OutputNotMature.selector);
        underwriter.claimLoss(INVOCATION_ID);
    }

    function test_claimLoss_doubleClaimReverts() public {
        (uint64 validUntil,) = _commitBuyOutput();

        vm.prank(trader);
        underwriter.purchaseCoverage(INVOCATION_ID, COVERAGE_AMOUNT, ESCROW_ID);

        vm.warp(validUntil + 1);
        oracle.setLatest(ASSET, (PRICE_AT_ISSUE * 90) / 100);

        vm.prank(trader);
        underwriter.claimLoss(INVOCATION_ID);

        vm.prank(trader);
        vm.expectRevert(IBU.AlreadyClaimed.selector);
        underwriter.claimLoss(INVOCATION_ID);
    }
}
