// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {IPriceOracle} from "../interfaces/external/IPriceOracle.sol";

contract MockPriceOracle is IPriceOracle {
    mapping(bytes32 asset => int256) public price;
    mapping(bytes32 asset => mapping(uint256 timestamp => int256)) public historicalPrice;
    mapping(bytes32 asset => uint256) public updatedAt;

    function setLatest(bytes32 asset, int256 newPrice) external {
        price[asset] = newPrice;
        updatedAt[asset] = block.timestamp;
    }

    function setPriceAt(bytes32 asset, uint256 timestamp, int256 newPrice) external {
        historicalPrice[asset][timestamp] = newPrice;
    }

    function latestAnswer(bytes32 asset) external view returns (int256, uint256) {
        return (price[asset], updatedAt[asset]);
    }

    function priceAt(bytes32 asset, uint256 timestamp) external view returns (int256) {
        return historicalPrice[asset][timestamp];
    }
}
