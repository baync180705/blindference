// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.28;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IEscrowReleaser} from "@blindference/contracts/interfaces/external/IEscrowReleaser.sol";
import {IBlindferenceAttestor} from "../interfaces/core/IBlindferenceAttestor.sol";
import {IBlindferenceUnderwriter} from "../interfaces/core/IBlindferenceUnderwriter.sol";
import {IPriceOracle} from "../interfaces/external/IPriceOracle.sol";

contract BlindferenceUnderwriter is TestnetCoreBase, IBlindferenceUnderwriter {
    /// @custom:storage-location erc7201:blindference.examples.BlindferenceUnderwriter
    struct Layout {
        IBlindferenceAttestor attestor;
        IPriceOracle priceOracle;
        IEscrowReleaser escrowReleaser;
        uint256 lossThreshold;
        uint256 holdTolerance;
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
        address escrowReleaser_,
        uint256 lossThresholdBps_,
        uint256 holdToleranceBps_
    ) external initializer {
        require(attestor_ != address(0) && priceOracle_ != address(0) && escrowReleaser_ != address(0), "ZeroAddress");
        require(lossThresholdBps_ > 0 && lossThresholdBps_ <= 10_000, "InvalidThreshold");

        __TestnetCoreBase_init(owner_);

        Layout storage l = _layout();
        l.attestor = IBlindferenceAttestor(attestor_);
        l.priceOracle = IPriceOracle(priceOracle_);
        l.escrowReleaser = IEscrowReleaser(escrowReleaser_);
        l.lossThreshold = lossThresholdBps_;
        l.holdTolerance = holdToleranceBps_;
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

    function claimLoss(uint256 invocationId) external nonReentrant {
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

        (int256 currentPrice,) = l.priceOracle.latestAnswer(output.asset);
        if (currentPrice <= 0 || output.priceAtIssue <= 0) {
            revert PriceUnavailable();
        }

        (uint256 lossBps, uint256 threshold) = _computeLoss(output, currentPrice);
        if (lossBps < threshold) {
            emit ClaimRejected(invocationId, buyer, "loss below threshold");
            revert LossBelowThreshold(lossBps, threshold);
        }

        uint256 payout = coverage.coverageAmount * lossBps / 10_000;
        if (payout > coverage.coverageAmount) {
            payout = coverage.coverageAmount;
        }

        coverage.claimed = true;
        l.escrowReleaser.release(coverage.escrowId, buyer, payout);

        emit ClaimPaid(invocationId, buyer, payout, output.priceAtIssue, currentPrice);
    }

    function coverageOf(uint256 invocationId, address buyer) external view returns (Coverage memory) {
        return _layout().coverages[invocationId][buyer];
    }

    function lossThresholdBps() external view returns (uint256) {
        return _layout().lossThreshold;
    }

    function holdToleranceBps() external view returns (uint256) {
        return _layout().holdTolerance;
    }

    function _computeLoss(IBlindferenceAttestor.InferenceOutput memory output, int256 currentPrice)
        private
        view
        returns (uint256 lossBps, uint256 threshold)
    {
        Layout storage l = _layout();
        threshold = l.lossThreshold;
        uint256 issuePrice = uint256(output.priceAtIssue);

        if (output.recommendation == IBlindferenceAttestor.Recommendation.BUY) {
            if (currentPrice < output.priceAtIssue) {
                uint256 drop = uint256(output.priceAtIssue - currentPrice);
                lossBps = drop * 10_000 / issuePrice;
            }
        } else if (output.recommendation == IBlindferenceAttestor.Recommendation.SELL) {
            if (currentPrice > output.priceAtIssue) {
                uint256 rise = uint256(currentPrice - output.priceAtIssue);
                lossBps = rise * 10_000 / issuePrice;
            }
        } else {
            uint256 absMove;
            if (currentPrice >= output.priceAtIssue) {
                absMove = uint256(currentPrice - output.priceAtIssue);
            } else {
                absMove = uint256(output.priceAtIssue - currentPrice);
            }
            uint256 holdMoveBps = absMove * 10_000 / issuePrice;
            if (holdMoveBps > l.holdTolerance) {
                lossBps = holdMoveBps - l.holdTolerance;
            }
        }
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly {
            l.slot := slot
        }
    }
}
