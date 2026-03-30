// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./InferenceEngine.sol";

contract BlindInference is InferenceEngine {
    event PredictionRequested(uint256 indexed requestId, address indexed requester, uint256 indexed modelId);

    constructor(address registryAddress, address escrowAddress)
        InferenceEngine(registryAddress, escrowAddress)
    {}

    function predict(uint256 requestId, inEuint32[] calldata encryptedInputs) external nonReentrant {
        (, uint256 modelId, , , , ) = escrow.escrows(requestId);
        emit PredictionRequested(requestId, msg.sender, modelId);
        _runInference(requestId, encryptedInputs);
    }
}
