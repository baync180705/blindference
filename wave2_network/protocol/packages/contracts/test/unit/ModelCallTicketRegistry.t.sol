// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {CoFheTest} from "@fhenixprotocol/cofhe-mock-contracts/CoFheTest.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {InEuint64} from "@fhenixprotocol/cofhe-contracts/FHE.sol";
import {ModelCallTicketRegistry} from "../../contracts/core/ModelCallTicketRegistry.sol";
import {IModelCallTicketRegistry} from "../../contracts/interfaces/core/IModelCallTicketRegistry.sol";
import {MockAgentIdentityRegistry} from "../../contracts/mocks/MockAgentIdentityRegistry.sol";
import {MockNodeOperatorRegistry} from "../../contracts/mocks/MockNodeOperatorRegistry.sol";
import {MockEscrow} from "../../contracts/mocks/MockEscrow.sol";

contract ModelCallTicketRegistryTest is CoFheTest {
    ModelCallTicketRegistry public registry;
    MockAgentIdentityRegistry public identity;
    MockNodeOperatorRegistry public nodes;
    MockEscrow public escrow;

    address public owner = makeAddr("owner");
    address public agentWallet = makeAddr("agentWallet");
    address public modelExecutor = makeAddr("modelExecutor");
    address public unauthorizedExecutor = makeAddr("unauthorizedExecutor");

    uint256 public constant AGENT_ID = 7;
    uint256 public constant MODEL_ID = 100;
    uint256 public constant INVOCATION_ID = 555;
    uint256 public constant ESCROW_ID = 999;

    function setUp() public {
        identity = new MockAgentIdentityRegistry();
        nodes = new MockNodeOperatorRegistry();
        escrow = new MockEscrow();

        identity.register(AGENT_ID, agentWallet);
        nodes.authorize(modelExecutor, MODEL_ID, true);
        escrow.setBudget(ESCROW_ID, true);

        ModelCallTicketRegistry impl = new ModelCallTicketRegistry(address(0));
        registry = ModelCallTicketRegistry(
            address(
                new ERC1967Proxy(
                    address(impl),
                    abi.encodeCall(
                        ModelCallTicketRegistry.initialize, (owner, address(escrow), address(identity), address(nodes))
                    )
                )
            )
        );
    }

    function _issue() internal returns (bytes32 ticketId) {
        InEuint64 memory fee = createInEuint64(1_000, agentWallet);
        vm.prank(agentWallet);
        ticketId = registry.issue(INVOCATION_ID, ESCROW_ID, AGENT_ID, MODEL_ID, fee, uint64(block.timestamp + 1 hours));
    }

    function test_issue_returnsDeterministicTicketId() public {
        bytes32 first = _issue();
        bytes32 second = _issue();
        assertTrue(first != second, "tickets should be unique per nonce");

        IModelCallTicketRegistry.Ticket memory t = registry.ticket(first);
        assertEq(t.invocationId, INVOCATION_ID);
        assertEq(t.escrowId, ESCROW_ID);
        assertEq(t.agentId, AGENT_ID);
        assertEq(t.modelId, MODEL_ID);
        assertFalse(t.consumed);
    }

    function test_issue_revertsWhenCallerIsNotAgentWallet() public {
        InEuint64 memory fee = createInEuint64(1_000, address(this));
        vm.expectRevert(IModelCallTicketRegistry.NotAgentWallet.selector);
        registry.issue(INVOCATION_ID, ESCROW_ID, AGENT_ID, MODEL_ID, fee, uint64(block.timestamp + 1 hours));
    }

    function test_issue_revertsWhenEscrowLacksBudget() public {
        escrow.setBudget(ESCROW_ID, false);
        InEuint64 memory fee = createInEuint64(1_000, agentWallet);

        vm.prank(agentWallet);
        vm.expectRevert(IModelCallTicketRegistry.InsufficientBudget.selector);
        registry.issue(INVOCATION_ID, ESCROW_ID, AGENT_ID, MODEL_ID, fee, uint64(block.timestamp + 1 hours));
    }

    function test_consume_marksTicketAndRecordsExecutor() public {
        bytes32 ticketId = _issue();

        vm.prank(modelExecutor);
        registry.consume(ticketId, bytes32("output"));

        IModelCallTicketRegistry.Ticket memory t = registry.ticket(ticketId);
        assertTrue(t.consumed);
        assertEq(t.executor, modelExecutor);
        assertEq(t.outputHash, bytes32("output"));

        bytes32[] memory consumed = registry.consumedTicketsOf(INVOCATION_ID);
        assertEq(consumed.length, 1);
        assertEq(consumed[0], ticketId);
    }

    function test_consume_revertsForUnauthorizedExecutor() public {
        bytes32 ticketId = _issue();

        vm.prank(unauthorizedExecutor);
        vm.expectRevert(IModelCallTicketRegistry.UnauthorizedExecutor.selector);
        registry.consume(ticketId, bytes32("output"));
    }

    function test_consume_revertsForExpiredTicket() public {
        bytes32 ticketId = _issue();
        skip(2 hours);

        vm.prank(modelExecutor);
        vm.expectRevert(IModelCallTicketRegistry.TicketStale.selector);
        registry.consume(ticketId, bytes32("output"));
    }

    function test_consume_revertsForUnknownTicket() public {
        vm.prank(modelExecutor);
        vm.expectRevert(IModelCallTicketRegistry.UnknownTicket.selector);
        registry.consume(bytes32("nope"), bytes32("output"));
    }

    function test_consume_revertsWhenAlreadyConsumed() public {
        bytes32 ticketId = _issue();

        vm.prank(modelExecutor);
        registry.consume(ticketId, bytes32("output"));

        vm.prank(modelExecutor);
        vm.expectRevert(IModelCallTicketRegistry.AlreadyConsumed.selector);
        registry.consume(ticketId, bytes32("output"));
    }

    function test_commitBatch_emitsEventForAgentWallet() public {
        vm.expectEmit(true, true, false, true);
        emit IModelCallTicketRegistry.BatchCommitted(INVOCATION_ID, AGENT_ID, bytes32("merkle"));
        vm.prank(agentWallet);
        registry.commitBatch(INVOCATION_ID, AGENT_ID, bytes32("merkle"));
    }

    function test_commitBatch_revertsForNonAgentWallet() public {
        vm.expectRevert(IModelCallTicketRegistry.NotAgentWallet.selector);
        registry.commitBatch(INVOCATION_ID, AGENT_ID, bytes32("merkle"));
    }

    function test_consumedTicketsOf_returnsAllInOrder() public {
        bytes32 t1 = _issue();
        bytes32 t2 = _issue();
        bytes32 t3 = _issue();

        vm.startPrank(modelExecutor);
        registry.consume(t2, bytes32("o2"));
        registry.consume(t1, bytes32("o1"));
        registry.consume(t3, bytes32("o3"));
        vm.stopPrank();

        bytes32[] memory consumed = registry.consumedTicketsOf(INVOCATION_ID);
        assertEq(consumed.length, 3);
        assertEq(consumed[0], t2);
        assertEq(consumed[1], t1);
        assertEq(consumed[2], t3);
    }
}
