// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IEscrowReleaser} from "@blindference/contracts/interfaces/external/IEscrowReleaser.sol";
import {ITradingSignalAttestor} from "../interfaces/core/ITradingSignalAttestor.sol";
import {ITradingLossUnderwriter} from "../interfaces/core/ITradingLossUnderwriter.sol";
import {IPriceOracle} from "../interfaces/external/IPriceOracle.sol";

contract TradingLossUnderwriter is TestnetCoreBase, ITradingLossUnderwriter {
    /// @custom:storage-location erc7201:blindference.examples.TradingLossUnderwriter
    struct Layout {
        ITradingSignalAttestor signalRegistry;
        IPriceOracle priceOracle;
        IEscrowReleaser escrowReleaser;
        uint256 lossThresholdBps;
        uint256 holdToleranceBps;
        mapping(uint256 invocationId => mapping(address buyer => Coverage)) coverages;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xa3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a300;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(
        address owner_,
        address signalRegistry_,
        address priceOracle_,
        address escrowReleaser_,
        uint256 lossThresholdBps_,
        uint256 holdToleranceBps_
    ) external initializer {
        require(
            signalRegistry_ != address(0) && priceOracle_ != address(0) && escrowReleaser_ != address(0), "ZeroAddress"
        );
        require(lossThresholdBps_ > 0 && lossThresholdBps_ <= 10_000, "InvalidThreshold");
        __TestnetCoreBase_init(owner_);

        Layout storage l = _layout();
        l.signalRegistry = ITradingSignalAttestor(signalRegistry_);
        l.priceOracle = IPriceOracle(priceOracle_);
        l.escrowReleaser = IEscrowReleaser(escrowReleaser_);
        l.lossThresholdBps = lossThresholdBps_;
        l.holdToleranceBps = holdToleranceBps_;
    }

    function purchaseCoverage(uint256 invocationId, uint256 coverageAmount, uint256 escrowId) external nonReentrant {
        if (coverageAmount == 0) {
            revert ZeroCoverage();
        }
        Layout storage l = _layout();
        address buyer = _msgSender();
        Coverage storage c = l.coverages[invocationId][buyer];
        if (c.purchasedAt != 0) {
            revert CoverageAlreadyPurchased();
        }
        l.signalRegistry.signalOf(invocationId);

        c.buyer = buyer;
        c.coverageAmount = coverageAmount;
        c.escrowId = escrowId;
        c.purchasedAt = uint64(block.timestamp);

        emit CoveragePurchased(invocationId, buyer, coverageAmount, escrowId);
    }

    function claimLoss(uint256 invocationId) external nonReentrant {
        Layout storage l = _layout();
        address buyer = _msgSender();
        Coverage storage c = l.coverages[invocationId][buyer];
        if (c.purchasedAt == 0) {
            revert CoverageMissing();
        }
        if (c.claimed) {
            revert AlreadyClaimed();
        }

        ITradingSignalAttestor.Signal memory signal = l.signalRegistry.signalOf(invocationId);
        if (block.timestamp < signal.validUntil) {
            revert SignalNotMature();
        }

        (int256 currentPrice,) = l.priceOracle.latestAnswer(signal.asset);
        if (currentPrice <= 0 || signal.priceAtIssue <= 0) {
            revert PriceUnavailable();
        }

        (uint256 lossBps, uint256 threshold) = _computeLoss(signal, currentPrice);
        if (lossBps < threshold) {
            emit ClaimRejected(invocationId, buyer, "loss below threshold");
            revert LossBelowThreshold(lossBps, threshold);
        }

        uint256 payout = c.coverageAmount * lossBps / 10_000;
        if (payout > c.coverageAmount) {
            payout = c.coverageAmount;
        }

        c.claimed = true;
        l.escrowReleaser.release(c.escrowId, buyer, payout);

        emit ClaimPaid(invocationId, buyer, payout, signal.priceAtIssue, currentPrice);
    }

    function coverageOf(uint256 invocationId, address buyer) external view returns (Coverage memory) {
        return _layout().coverages[invocationId][buyer];
    }

    function lossThresholdBps() external view returns (uint256) {
        return _layout().lossThresholdBps;
    }

    function holdToleranceBps() external view returns (uint256) {
        return _layout().holdToleranceBps;
    }

    function _computeLoss(ITradingSignalAttestor.Signal memory signal, int256 currentPrice)
        private
        view
        returns (uint256 lossBps, uint256 threshold)
    {
        Layout storage l = _layout();
        threshold = l.lossThresholdBps;
        uint256 issuePrice = uint256(signal.priceAtIssue);

        if (signal.direction == ITradingSignalAttestor.Direction.BUY) {
            // Loss for a BUY signal = price went down.
            if (currentPrice < signal.priceAtIssue) {
                uint256 drop = uint256(signal.priceAtIssue - currentPrice);
                lossBps = drop * 10_000 / issuePrice;
            }
        } else if (signal.direction == ITradingSignalAttestor.Direction.SELL) {
            // Loss for a SELL signal = price went up.
            if (currentPrice > signal.priceAtIssue) {
                uint256 rise = uint256(currentPrice - signal.priceAtIssue);
                lossBps = rise * 10_000 / issuePrice;
            }
        } else {
            // HOLD: any large move in either direction = signal was wrong.
            uint256 absMove;
            if (currentPrice >= signal.priceAtIssue) {
                absMove = uint256(currentPrice - signal.priceAtIssue);
            } else {
                absMove = uint256(signal.priceAtIssue - currentPrice);
            }
            uint256 holdMoveBps = absMove * 10_000 / issuePrice;
            if (holdMoveBps > l.holdToleranceBps) {
                lossBps = holdMoveBps - l.holdToleranceBps;
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
