// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

/// @notice Chainlink-shaped price feed.
interface IPriceOracle {
    function latestAnswer(bytes32 asset) external view returns (int256 price, uint256 updatedAt);
    function priceAt(bytes32 asset, uint256 timestamp) external view returns (int256 price);
    function getDefaultOutcome(string calldata loanId) external view returns (bool);
}
