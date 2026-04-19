// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IPriceOracle {
    function getPrice(string calldata asset, uint256 timestamp) external view returns (uint256);
}

contract MockPriceOracle is IPriceOracle {
    mapping(string => uint256) public prices;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function setPrice(string calldata asset, uint256 price) external onlyOwner {
        prices[asset] = price;
    }

    function getPrice(string calldata asset, uint256) external view override returns (uint256) {
        require(prices[asset] > 0, "Price not set");
        return prices[asset];
    }
}
