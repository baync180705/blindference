// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@fhenixprotocol/contracts/FHE.sol";

// --- INTERFACES ---

interface IModelRegistry {
    function getWeightHandles(uint256 _modelId) external view returns (euint32[] memory);
    function getBiasHandle(uint256 _modelId) external view returns (euint32);
}

interface IPaymentEscrow {
    function markProcessing(uint256 _requestId) external;
    function release(uint256 _requestId) external;
    function escrows(uint256 _requestId) external view returns (
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

    // --- EVM GAS LIMIT PROTECTION ---
    // FHE math is expensive. This prevents the unbounded loop gas-limit bomb.
    // For a Buildathon demo, a max of 15 weights (e.g., Logistic Regression) is safe.
    uint256 public constant MAX_WEIGHTS_PER_BLOCK = 15;

    // --- REENTRANCY GUARD ---
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

    constructor(address _registryAddress, address _escrowAddress) {
        owner = msg.sender;
        registry = IModelRegistry(_registryAddress);
        escrow = IPaymentEscrow(_escrowAddress);
        _status = _NOT_ENTERED;
    }

    /**
     * @dev Executes the machine learning model entirely on ciphertext.
     */
    function runInference(uint256 _requestId, inEuint32[] calldata _encryptedInputs) external nonReentrant {
        
        // 1. Fetch and Validate Escrow Record
        (address requester, uint256 modelId, , , uint8 status, ) = escrow.escrows(_requestId);
        require(msg.sender == requester, "Not the authorized requester");
        require(status == 1, "Request is not PENDING"); 
        
        // 2. Lock State to prevent "Free Inference" refund exploit
        escrow.markProcessing(_requestId);

        // 3. Fetch Weights & Bias
        euint32[] memory weights = registry.getWeightHandles(modelId);
        euint32 bias = registry.getBiasHandle(modelId);
        
        // 4. Validate Constraints (Dimensions & Gas Limits)
        require(weights.length > 0, "Model has no weights");
        require(weights.length <= MAX_WEIGHTS_PER_BLOCK, "Model exceeds FHE block gas limit");
        require(weights.length == _encryptedInputs.length, "Input and Weight dimension mismatch");

        // 5. Execute FHE Arithmetic (y = wx + b)
        euint32 sum = FHE.asEuint32(0);
        
        for (uint256 i = 0; i < weights.length; i++) {
            euint32 encryptedInput = FHE.asEuint32(_encryptedInputs[i]);
            euint32 product = FHE.mul(encryptedInput, weights[i]);
            sum = FHE.add(sum, product);
        }

        // Add the bias term
        sum = FHE.add(sum, bias);

        // 6. Encrypted Activation Function (Thresholding)
        // Since FHE cannot do standard if/else branches, we use FHE.select.
        // Assuming models output logits and are quantized so 128 is the decision boundary:
        // If sum >= 128, return encrypted 1 (High Risk). Else return encrypted 0 (Low Risk).
        
        euint32 threshold = FHE.asEuint32(128); // Standard midpoint for 8-bit unsigned quantization
        ebool isHighRisk = FHE.gte(sum, threshold);
        
        euint32 finalDiagnosis = FHE.select(isHighRisk, FHE.asEuint32(1), FHE.asEuint32(0));

        // 7. Cryptographically Seal the Result to the Requester
        FHE.allowSender(finalDiagnosis);
        results[_requestId] = finalDiagnosis;

        // 8. Atomic Payment Release
        escrow.release(_requestId);

        emit InferenceCompleted(_requestId, msg.sender);
    }

    /**
     * @dev Called by the frontend to fetch the encrypted handle for local decryption.
     */
    function getResult(uint256 _requestId) external view returns (euint32) {
        (address requester, , , , , ) = escrow.escrows(_requestId);
        require(msg.sender == requester, "Not authorized to view this result");
        require(results[_requestId].isInitialized(), "Result not ready or failed");
        
        return results[_requestId];
    }
}