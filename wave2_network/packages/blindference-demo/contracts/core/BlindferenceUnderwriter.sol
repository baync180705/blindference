// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.28;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IEscrowReleaser} from "@blindference/contracts/interfaces/external/IEscrowReleaser.sol";
import {IBlindferenceAttestor} from "../interfaces/core/IBlindferenceAttestor.sol";
import {IBlindferenceUnderwriter} from "../interfaces/core/IBlindferenceUnderwriter.sol";
import {IPriceOracle} from "../interfaces/external/IPriceOracle.sol";

contract BlindferenceUnderwriter is TestnetCoreBase, IBlindferenceUnderwriter {
    uint256 public constant RISK_THRESHOLD = 50;

    /// @custom:storage-location erc7201:blindference.examples.BlindferenceUnderwriter
    struct Layout {
        IBlindferenceAttestor attestor;
        IPriceOracle priceOracle;
        IEscrowReleaser escrowReleaser;
        mapping(uint256 invocationId => mapping(address buyer => Coverage)) coverages;
    }

    bytes32 private constant _LAYOUT_SLOT = 0x4127d4eeb04b4326294f73907e73fe88cf64867df6b077aa35692dc39af96f00;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(
        address owner_,
        address attestor_,
        address priceOracle_,
        address escrowReleaser_
    ) external initializer {
        require(attestor_ != address(0) && priceOracle_ != address(0) && escrowReleaser_ != address(0), "ZeroAddress");

        __TestnetCoreBase_init(owner_);

        Layout storage l = _layout();
        l.attestor = IBlindferenceAttestor(attestor_);
        l.priceOracle = IPriceOracle(priceOracle_);
        l.escrowReleaser = IEscrowReleaser(escrowReleaser_);
    }

    function purchaseCoverage(uint256 invocationId, uint256 coverageAmount, uint256 escrowId) external nonReentrant {
        if (coverageAmount == 0) {
            revert ZeroCoverage();
        }

        Layout storage l = _layout();
        address buyer = _msgSender();
        Coverage storage coverage = l.coverages[invocationId][buyer];
        if (coverage.purchasedAt != 0) {
            revert CoverageAlreadyPurchased();
        }

        l.attestor.outputOf(invocationId);

        coverage.buyer = buyer;
        coverage.coverageAmount = coverageAmount;
        coverage.escrowId = escrowId;
        coverage.purchasedAt = uint64(block.timestamp);

        emit CoveragePurchased(invocationId, buyer, coverageAmount, escrowId);
    }

    function claimLoss(uint256 invocationId, string calldata loanId) external nonReentrant {
        Layout storage l = _layout();
        address buyer = _msgSender();
        Coverage storage coverage = l.coverages[invocationId][buyer];
        if (coverage.purchasedAt == 0) {
            revert CoverageMissing();
        }
        if (coverage.claimed) {
            revert AlreadyClaimed();
        }

        IBlindferenceAttestor.InferenceOutput memory output = l.attestor.outputOf(invocationId);
        if (block.timestamp < output.validUntil) {
            revert OutputNotMature();
        }

        if (keccak256(bytes(loanId)) != output.loanIdHash) {
            revert LoanIdMismatch();
        }

        bool predictedHighRisk = output.riskScore >= uint8(RISK_THRESHOLD);
        bool actuallyDefaulted = l.priceOracle.getDefaultOutcome(loanId);
        if (predictedHighRisk == actuallyDefaulted) {
            emit ClaimRejected(invocationId, buyer, "prediction was correct");
            revert PredictionCorrect();
        }

        coverage.claimed = true;
        uint256 payout = coverage.coverageAmount;
        l.escrowReleaser.release(coverage.escrowId, buyer, payout);

        emit ClaimPaid(invocationId, buyer, payout, output.riskScore, actuallyDefaulted);
    }

    function coverageOf(uint256 invocationId, address buyer) external view returns (Coverage memory) {
        return _layout().coverages[invocationId][buyer];
    }

    function riskThreshold() external pure returns (uint256) {
        return RISK_THRESHOLD;
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly {
            l.slot := slot
        }
    }
}
