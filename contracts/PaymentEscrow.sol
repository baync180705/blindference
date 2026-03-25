// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

interface IModelRegistry {
    function getPrice(uint256 _modelId) external view returns (uint256);
    function getLabWallet(uint256 _modelId) external view returns (address);
}

contract PaymentEscrow {
    address public owner;
    address public inferenceEngine;
    address public feeTreasury; // Marketplace revenue wallet
    
    IERC20 public paymentToken;
    IModelRegistry public registry;

    uint256 public protocolFeeBps = 250; // 2.5% fee (Basis Points: 10000 = 100%)
    uint256 public constant TIMEOUT_DURATION = 24 hours;
    
    uint256 public requestCount;

    enum RequestStatus { NONE, PENDING, PROCESSING, COMPLETED, REFUNDED }

    struct EscrowRecord {
        address requester;
        uint256 modelId;
        uint256 amount;
        address labWallet;
        RequestStatus status;
        uint256 timestamp;
    }

    // Mapping maps a unique Request ID to its escrow state
    mapping(uint256 => EscrowRecord) public escrows;

    // --- REENTRANCY GUARD ---
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyEngine() {
        require(msg.sender == inferenceEngine, "Only InferenceEngine");
        _;
    }

    event FeeLocked(uint256 indexed requestId, address indexed requester, uint256 indexed modelId, uint256 amount);
    event ProcessingStarted(uint256 indexed requestId);
    event FeeReleased(uint256 indexed requestId, address indexed labWallet, uint256 labAmount, uint256 protocolAmount);
    event FeeRefunded(uint256 indexed requestId, address indexed requester, uint256 amount);

    constructor(address _paymentTokenAddress, address _registryAddress, address _feeTreasury) {
        owner = msg.sender;
        feeTreasury = _feeTreasury;
        paymentToken = IERC20(_paymentTokenAddress);
        registry = IModelRegistry(_registryAddress);
        _status = _NOT_ENTERED;
    }

    function setInferenceEngine(address _engine) external onlyOwner {
        inferenceEngine = _engine;
    }

    function setProtocolFee(uint256 _bps) external onlyOwner {
        require(_bps <= 1000, "Fee cannot exceed 10%");
        protocolFeeBps = _bps;
    }

    /**
     * @dev Step 1: User locks fee. Generates a unique requestId for concurrency.
     */
    function lockFee(uint256 _modelId) external nonReentrant returns (uint256) {
        uint256 price = registry.getPrice(_modelId);
        address lab = registry.getLabWallet(_modelId);

        requestCount++;
        uint256 requestId = requestCount;

        escrows[requestId] = EscrowRecord({
            requester: msg.sender,
            modelId: _modelId,
            amount: price,
            labWallet: lab,
            status: RequestStatus.PENDING,
            timestamp: block.timestamp
        });

        if (price > 0) {
            require(
                paymentToken.transferFrom(msg.sender, address(this), price),
                "Token transfer failed. Check allowance."
            );
        }

        emit FeeLocked(requestId, msg.sender, _modelId, price);
        return requestId;
    }

    /**
     * @dev Step 2: Engine locks the refund to prevent the "Free Inference" exploit.
     */
    function markProcessing(uint256 _requestId) external onlyEngine {
        require(escrows[_requestId].status == RequestStatus.PENDING, "Request not PENDING");
        escrows[_requestId].status = RequestStatus.PROCESSING;
        emit ProcessingStarted(_requestId);
    }

    /**
     * @dev Step 3: Engine finishes math, releases funds, takes platform cut.
     */
    function release(uint256 _requestId) external onlyEngine nonReentrant {
        EscrowRecord storage record = escrows[_requestId];
        require(record.status == RequestStatus.PROCESSING, "Request not PROCESSING");

        record.status = RequestStatus.COMPLETED;

        uint256 totalAmount = record.amount;
        if (totalAmount > 0) {
            uint256 protocolCut = (totalAmount * protocolFeeBps) / 10000;
            uint256 labCut = totalAmount - protocolCut;

            if (protocolCut > 0) {
                require(paymentToken.transfer(feeTreasury, protocolCut), "Protocol fee transfer failed");
            }
            if (labCut > 0) {
                require(paymentToken.transfer(record.labWallet, labCut), "Lab fee transfer failed");
            }
            
            emit FeeReleased(_requestId, record.labWallet, labCut, protocolCut);
        } else {
            emit FeeReleased(_requestId, record.labWallet, 0, 0);
        }
    }

    /**
     * @dev Standard refund if the user cancels before inference starts.
     */
    function refund(uint256 _requestId) external nonReentrant {
        EscrowRecord storage record = escrows[_requestId];
        require(record.requester == msg.sender, "Not your request");
        require(record.status == RequestStatus.PENDING, "Cannot refund: Processing started");

        record.status = RequestStatus.REFUNDED;

        if (record.amount > 0) {
            require(paymentToken.transfer(msg.sender, record.amount), "Refund transfer failed");
        }

        emit FeeRefunded(_requestId, msg.sender, record.amount);
    }

    /**
     * @dev Emergency hatch if the FHE math reverts/stalls and traps funds in PROCESSING.
     */
    function forceRefund(uint256 _requestId) external nonReentrant {
        EscrowRecord storage record = escrows[_requestId];
        require(record.requester == msg.sender, "Not your request");
        require(record.status == RequestStatus.PROCESSING, "Not PROCESSING");
        require(block.timestamp > record.timestamp + TIMEOUT_DURATION, "Timeout period not reached");

        record.status = RequestStatus.REFUNDED;

        if (record.amount > 0) {
            require(paymentToken.transfer(msg.sender, record.amount), "Force refund failed");
        }

        emit FeeRefunded(_requestId, msg.sender, record.amount);
    }

    function getRequestStatus(uint256 _requestId) external view returns (RequestStatus) {
        return escrows[_requestId].status;
    }
}