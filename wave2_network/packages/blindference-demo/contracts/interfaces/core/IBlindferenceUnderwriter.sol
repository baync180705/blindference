// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.28;

interface IBlindferenceUnderwriter {
    struct Coverage {
        address buyer;
        uint256 coverageAmount;
        uint256 escrowId;
        uint64 purchasedAt;
        bool claimed;
    }

    event CoveragePurchased(
        uint256 indexed invocationId, address indexed buyer, uint256 coverageAmount, uint256 escrowId
    );
    event ClaimPaid(
        uint256 indexed invocationId,
        address indexed buyer,
        uint256 payoutAmount,
        uint8 riskScore,
        bool defaulted
    );
    event ClaimRejected(uint256 indexed invocationId, address indexed buyer, string reason);

    error CoverageAlreadyPurchased();
    error CoverageMissing();
    error AlreadyClaimed();
    error OutputNotMature();
    error LoanIdMismatch();
    error PredictionCorrect();
    error ZeroCoverage();

    function purchaseCoverage(uint256 invocationId, uint256 coverageAmount, uint256 escrowId) external;

    function claimLoss(uint256 invocationId, string calldata loanId) external;

    function coverageOf(uint256 invocationId, address buyer) external view returns (Coverage memory);

    function riskThreshold() external pure returns (uint256);
}
