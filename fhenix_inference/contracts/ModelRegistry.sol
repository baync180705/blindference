// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@fhenixprotocol/contracts/FHE.sol";

contract ModelRegistry {
    address public owner;
    address public inferenceEngine;

    struct Model {
        uint256 modelId;
        address labWallet;
        uint256 pricePerQuery;
        string ipfsHash;
        euint32[] weightHandles;
        euint32 biasHandle;
        bool active;
    }

    mapping(uint256 => Model) public models;
    uint256 public modelCount;

    event ModelRegistered(uint256 indexed modelId, address indexed labWallet, uint256 pricePerQuery);
    event ModelDeactivated(uint256 indexed modelId);
    event PriceUpdated(uint256 indexed modelId, uint256 newPrice);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not registry owner");
        _;
    }

    modifier onlyLab(uint256 modelId) {
        require(msg.sender == models[modelId].labWallet, "Not the AI lab");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setInferenceEngine(address engine) external onlyOwner {
        inferenceEngine = engine;
    }

    function registerModel(
        inEuint32[] calldata encryptedWeights,
        inEuint32 calldata encryptedBias,
        uint256 pricePerQuery,
        string calldata ipfsHash
    ) external returns (uint256) {
        require(inferenceEngine != address(0), "Inference engine not linked");

        modelCount++;
        uint256 newModelId = modelCount;
        Model storage newModel = models[newModelId];

        newModel.modelId = newModelId;
        newModel.labWallet = msg.sender;
        newModel.pricePerQuery = pricePerQuery;
        newModel.ipfsHash = ipfsHash;
        newModel.active = true;

        for (uint256 i = 0; i < encryptedWeights.length; i++) {
            euint32 weightHandle = FHE.asEuint32(encryptedWeights[i]);
            newModel.weightHandles.push(weightHandle);
        }

        euint32 bias = FHE.asEuint32(encryptedBias);
        newModel.biasHandle = bias;

        emit ModelRegistered(newModelId, msg.sender, pricePerQuery);
        return newModelId;
    }

    function deactivateModel(uint256 modelId) external onlyLab(modelId) {
        models[modelId].active = false;
        emit ModelDeactivated(modelId);
    }

    function updatePrice(uint256 modelId, uint256 newPrice) external onlyLab(modelId) {
        models[modelId].pricePerQuery = newPrice;
        emit PriceUpdated(modelId, newPrice);
    }

    function getWeightHandles(uint256 modelId) external view returns (euint32[] memory) {
        require(models[modelId].active, "Model inactive");
        return models[modelId].weightHandles;
    }

    function getBiasHandle(uint256 modelId) external view returns (euint32) {
        require(models[modelId].active, "Model inactive");
        return models[modelId].biasHandle;
    }

    function getLabWallet(uint256 modelId) external view returns (address) {
        require(models[modelId].active, "Model inactive");
        return models[modelId].labWallet;
    }

    function getPrice(uint256 modelId) external view returns (uint256) {
        require(models[modelId].active, "Model inactive");
        return models[modelId].pricePerQuery;
    }

    function getIpfsHash(uint256 modelId) external view returns (string memory) {
        require(models[modelId].active, "Model inactive");
        return models[modelId].ipfsHash;
    }
}
