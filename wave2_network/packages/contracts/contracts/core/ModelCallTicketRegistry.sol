// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {euint64, InEuint64} from "@fhenixprotocol/cofhe-contracts/FHE.sol";
import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {FHEMeta} from "@reineira-os/shared/contracts/common/FHEMeta.sol";
import {IEscrow} from "@reineira-os/shared/contracts/interfaces/core/IEscrow.sol";
import {IModelCallTicketRegistry} from "../interfaces/core/IModelCallTicketRegistry.sol";
import {INodeOperatorRegistry} from "../interfaces/core/INodeOperatorRegistry.sol";
import {IAgentIdentityRegistry} from "../interfaces/external/IAgentIdentityRegistry.sol";

contract ModelCallTicketRegistry is TestnetCoreBase, IModelCallTicketRegistry {
    /// @custom:storage-location erc7201:reineira.blindference.ModelCallTicketRegistry
    struct Layout {
        IEscrow escrow;
        IAgentIdentityRegistry identity;
        INodeOperatorRegistry nodes;
        mapping(bytes32 ticketId => Ticket) tickets;
        mapping(uint256 invocationId => uint256) issuanceNonce;
        mapping(uint256 invocationId => bytes32[]) consumedByInvocation;
    }

    bytes32 private constant _LAYOUT_SLOT = 0x4f1d2c8a6e0b3f7c9a1d5e8b2c4f6a8e0c2d4f6b8a0c2e4d6f8b0a2c4e6d8f00;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(address owner_, address escrow_, address identity_, address nodes_) external initializer {
        require(escrow_ != address(0) && identity_ != address(0) && nodes_ != address(0), "ZeroAddress");
        __TestnetCoreBase_init(owner_);
        Layout storage l = _layout();
        l.escrow = IEscrow(escrow_);
        l.identity = IAgentIdentityRegistry(identity_);
        l.nodes = INodeOperatorRegistry(nodes_);
    }

    function issue(
        uint256 invocationId,
        uint256 escrowId,
        uint256 agentId,
        uint256 modelId,
        InEuint64 calldata modelFee,
        uint64 expiresAt
    ) external nonReentrant returns (bytes32 ticketId) {
        Layout storage l = _layout();
        address sender = _msgSender();

        if (sender != l.identity.walletOf(agentId)) {
            revert NotAgentWallet();
        }

        euint64 fee = FHEMeta.asEuint64(modelFee, sender);
        if (!l.escrow.hasBudget(escrowId, sender, fee)) {
            revert InsufficientBudget();
        }

        uint256 nonce;
        unchecked {
            nonce = ++l.issuanceNonce[invocationId];
        }

        ticketId = keccak256(abi.encode(invocationId, modelId, nonce));

        l.tickets[ticketId] = Ticket({
            invocationId: invocationId,
            escrowId: escrowId,
            agentId: agentId,
            modelId: modelId,
            modelFee: fee,
            expiresAt: expiresAt,
            consumed: false,
            outputHash: bytes32(0),
            executor: address(0)
        });

        emit TicketIssued(ticketId, invocationId, agentId, modelId);
    }

    function commitBatch(uint256 invocationId, uint256 agentId, bytes32 merkleRoot) external nonReentrant {
        Layout storage l = _layout();
        if (_msgSender() != l.identity.walletOf(agentId)) {
            revert NotAgentWallet();
        }
        emit BatchCommitted(invocationId, agentId, merkleRoot);
    }

    function consume(bytes32 ticketId, bytes32 outputHash) external nonReentrant {
        Layout storage l = _layout();
        Ticket storage t = l.tickets[ticketId];

        if (t.expiresAt == 0) {
            revert UnknownTicket();
        }
        if (t.consumed) {
            revert AlreadyConsumed();
        }
        if (block.timestamp >= t.expiresAt) {
            revert TicketStale();
        }

        address executor = _msgSender();
        if (!l.nodes.modelExecutorAuthorized(executor, t.modelId)) {
            revert UnauthorizedExecutor();
        }

        t.consumed = true;
        t.outputHash = outputHash;
        t.executor = executor;

        l.consumedByInvocation[t.invocationId].push(ticketId);

        emit TicketConsumed(ticketId, executor, outputHash);
    }

    function ticket(bytes32 ticketId) external view returns (Ticket memory) {
        return _layout().tickets[ticketId];
    }

    function consumedTicketsOf(uint256 invocationId) external view returns (bytes32[] memory) {
        return _layout().consumedByInvocation[invocationId];
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
