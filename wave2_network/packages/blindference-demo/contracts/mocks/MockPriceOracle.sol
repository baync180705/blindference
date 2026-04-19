// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.28;

import {IPriceOracle} from "../interfaces/external/IPriceOracle.sol";

/// @notice Demo-controlled oracle that exposes both the Blindference demo feed
/// shape (`latestAnswer`) and a simple string-based helper for manual ops.
contract MockPriceOracle is IPriceOracle {
    mapping(bytes32 asset => int256) public price;
    mapping(bytes32 asset => mapping(uint256 timestamp => int256)) public historicalPrice;
    mapping(bytes32 asset => uint256) public updatedAt;
    address public owner;

    error NotOwner();
    error PriceNotSet();

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) {
            revert NotOwner();
        }
        _;
    }

    function setLatest(bytes32 asset, int256 newPrice) external onlyOwner {
        price[asset] = newPrice;
        updatedAt[asset] = block.timestamp;
    }

    function setPriceAt(bytes32 asset, uint256 timestamp, int256 newPrice) external onlyOwner {
        historicalPrice[asset][timestamp] = newPrice;
    }

    function setPrice(string calldata asset, uint256 newPrice) external onlyOwner {
        bytes32 assetKey = keccak256(bytes(asset));
        price[assetKey] = int256(newPrice);
        updatedAt[assetKey] = block.timestamp;
    }

    function getPrice(string calldata asset, uint256 timestamp) external view returns (uint256) {
        bytes32 assetKey = keccak256(bytes(asset));
        int256 value = timestamp == 0 ? price[assetKey] : historicalPrice[assetKey][timestamp];
        if (value <= 0) {
            revert PriceNotSet();
        }
        return uint256(value);
    }

    function latestAnswer(bytes32 asset) external view returns (int256, uint256) {
        return (price[asset], updatedAt[asset]);
    }

    function priceAt(bytes32 asset, uint256 timestamp) external view returns (int256) {
        return historicalPrice[asset][timestamp];
    }
}
