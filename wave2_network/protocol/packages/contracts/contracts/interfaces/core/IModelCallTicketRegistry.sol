// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {euint64, InEuint64} from "@fhenixprotocol/cofhe-contracts/FHE.sol";

interface IModelCallTicketRegistry {
    struct Ticket {
        uint256 invocationId;
        uint256 escrowId;
        uint256 agentId;
        uint256 modelId;
        euint64 modelFee;
        uint64 expiresAt;
        bool consumed;
        bytes32 outputHash;
        address executor;
    }

    event TicketIssued(bytes32 indexed ticketId, uint256 indexed invocationId, uint256 agentId, uint256 modelId);
    event TicketConsumed(bytes32 indexed ticketId, address indexed executor, bytes32 outputHash);
    event BatchCommitted(uint256 indexed invocationId, uint256 indexed agentId, bytes32 merkleRoot);

    error NotAgentWallet();
    error InsufficientBudget();
    error TicketStale();
    error AlreadyConsumed();
    error UnauthorizedExecutor();
    error UnknownTicket();

    function issue(
        uint256 invocationId,
        uint256 escrowId,
        uint256 agentId,
        uint256 modelId,
        InEuint64 calldata modelFee,
        uint64 expiresAt
    ) external returns (bytes32 ticketId);

    function commitBatch(uint256 invocationId, uint256 agentId, bytes32 merkleRoot) external;

    function consume(bytes32 ticketId, bytes32 outputHash) external;

    function ticket(bytes32 ticketId) external view returns (Ticket memory);
    function consumedTicketsOf(uint256 invocationId) external view returns (bytes32[] memory);
}
