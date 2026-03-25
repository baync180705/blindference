// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

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
        euint32 biasHandle;         // NEW: Stores the encrypted bias term
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

    modifier onlyLab(uint256 _modelId) {
        require(msg.sender == models[_modelId].labWallet, "Not the AI lab");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setInferenceEngine(address _engine) external onlyOwner {
        inferenceEngine = _engine;
    }

    function registerModel(
        inEuint32[] calldata _encryptedWeights, 
        inEuint32 calldata _encryptedBias,     // NEW: Ingests the encrypted bias
        uint256 _pricePerQuery,
        string calldata _ipfsHash
    ) external returns (uint256) {
        require(inferenceEngine != address(0), "Inference engine not linked");
        
        modelCount++;
        uint256 newModelId = modelCount;

        Model storage newModel = models[newModelId];
        newModel.modelId = newModelId;
        newModel.labWallet = msg.sender;
        newModel.pricePerQuery = _pricePerQuery;
        newModel.ipfsHash = _ipfsHash;
        newModel.active = true;

        // 1. Process and permission the weights
        for (uint256 i = 0; i < _encryptedWeights.length; i++) {
            euint32 weightHandle = FHE.asEuint32(_encryptedWeights[i]);
            FHE.allow(weightHandle, inferenceEngine);
            newModel.weightHandles.push(weightHandle);
        }

        // 2. Process and permission the bias term
        euint32 bias = FHE.asEuint32(_encryptedBias);
        FHE.allow(bias, inferenceEngine);
        newModel.biasHandle = bias;

        emit ModelRegistered(newModelId, msg.sender, _pricePerQuery);
        return newModelId;
    }

    // --- LAB CONTROLS ---

    function deactivateModel(uint256 _modelId) external onlyLab(_modelId) {
        models[_modelId].active = false;
        emit ModelDeactivated(_modelId);
    }

    function updatePrice(uint256 _modelId, uint256 _newPrice) external onlyLab(_modelId) {
        models[_modelId].pricePerQuery = _newPrice;
        emit PriceUpdated(_modelId, _newPrice);
    }

    // --- GETTERS ---

    function getWeightHandles(uint256 _modelId) external view returns (euint32[] memory) {
        require(models[_modelId].active, "Model inactive");
        return models[_modelId].weightHandles;
    }

    function getBiasHandle(uint256 _modelId) external view returns (euint32) {
        require(models[_modelId].active, "Model inactive");
        return models[_modelId].biasHandle;
    }

    function getLabWallet(uint256 _modelId) external view returns (address) {
        require(models[_modelId].active, "Model inactive");
        return models[_modelId].labWallet;
    }

    function getPrice(uint256 _modelId) external view returns (uint256) {
        require(models[_modelId].active, "Model inactive");
        return models[_modelId].pricePerQuery;
    }

    function getIpfsHash(uint256 _modelId) external view returns (string memory) {
        require(models[_modelId].active, "Model inactive");
        return models[_modelId].ipfsHash;
    }
}