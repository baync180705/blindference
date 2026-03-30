// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@fhenixprotocol/contracts/FHE.sol";

interface IModelRegistry {
    function getWeightHandles(uint256 modelId) external view returns (euint32[] memory);
    function getBiasHandle(uint256 modelId) external view returns (euint32);
}

interface IPaymentEscrow {
    function markProcessing(uint256 requestId) external;
    function release(uint256 requestId) external;
    function escrows(uint256 requestId) external view returns (
        address requester,
        uint256 modelId,
        uint256 amount,
        address labWallet,
        uint8 status,
        uint256 timestamp
    );
}

contract InferenceEngine {
    address public owner;
    IModelRegistry public registry;
    IPaymentEscrow public escrow;

    uint256 public constant MAX_WEIGHTS_PER_BLOCK = 15;

    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    mapping(uint256 => euint32) private results;

    event InferenceCompleted(uint256 indexed requestId, address indexed requester);

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }

    constructor(address registryAddress, address escrowAddress) {
        owner = msg.sender;
        registry = IModelRegistry(registryAddress);
        escrow = IPaymentEscrow(escrowAddress);
        _status = _NOT_ENTERED;
    }

    function runInference(uint256 requestId, inEuint32[] calldata encryptedInputs) external virtual nonReentrant {
        _runInference(requestId, encryptedInputs);
    }

    function _runInference(uint256 requestId, inEuint32[] calldata encryptedInputs) internal {
        (address requester, uint256 modelId, , , uint8 status, ) = escrow.escrows(requestId);
        require(msg.sender == requester, "Not the authorized requester");
        require(status == 1, "Request is not PENDING");

        escrow.markProcessing(requestId);

        euint32[] memory weights = registry.getWeightHandles(modelId);
        euint32 bias = registry.getBiasHandle(modelId);

        require(weights.length > 0, "Model has no weights");
        require(weights.length <= MAX_WEIGHTS_PER_BLOCK, "Model exceeds FHE block gas limit");
        require(weights.length == encryptedInputs.length, "Input and Weight dimension mismatch");

        // Keep inference on native euint32 lanes so coFHE can accelerate the dot product and activation.
        euint32 sum = FHE.asEuint32(0);
        for (uint256 i = 0; i < weights.length; i++) {
            euint32 encryptedInput = FHE.asEuint32(encryptedInputs[i]);
            sum = FHE.add(sum, FHE.mul(encryptedInput, weights[i]));
        }

        sum = FHE.add(sum, bias);

        // Activation is expressed with native FHE comparison/select primitives only.
        euint32 threshold = FHE.asEuint32(128);
        ebool isHighRisk = FHE.gte(sum, threshold);
        euint32 finalDiagnosis = FHE.select(isHighRisk, FHE.asEuint32(1), FHE.asEuint32(0));

        results[requestId] = finalDiagnosis;

        escrow.release(requestId);
        emit InferenceCompleted(requestId, msg.sender);
    }

    function getResult(uint256 requestId) external view returns (euint32) {
        (address requester, , , , , ) = escrow.escrows(requestId);
        require(msg.sender == requester, "Not authorized to view this result");
        require(FHE.isInitialized(results[requestId]), "Result not ready or failed");

        return results[requestId];
    }
}
