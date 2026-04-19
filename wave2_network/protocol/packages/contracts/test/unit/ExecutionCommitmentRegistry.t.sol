// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {ExecutionCommitmentRegistry} from "../../contracts/core/ExecutionCommitmentRegistry.sol";
import {IExecutionCommitmentRegistry as IECR} from "../../contracts/interfaces/core/IExecutionCommitmentRegistry.sol";

contract ExecutionCommitmentRegistryTest is Test {
    ExecutionCommitmentRegistry public registry;

    address public owner = makeAddr("owner");
    address public dispatcher = makeAddr("dispatcher");
    address public executor = makeAddr("executor");
    address public crossVerifier = makeAddr("crossVerifier");
    address public outsider = makeAddr("outsider");

    uint256 public constant INVOCATION_ID = 42;
    uint256 public constant ESCROW_ID = 9001;
    uint256 public constant AGENT_ID = 7;

    bytes32 public constant OUTPUT_HANDLE_OK = bytes32(uint256(0xCAFE));
    bytes32 public constant OUTPUT_HANDLE_BAD = bytes32(uint256(0xBEEF));
    bytes32 public constant SALT_E = bytes32(uint256(0x11));
    bytes32 public constant SALT_V = bytes32(uint256(0x22));

    function setUp() public {
        ExecutionCommitmentRegistry impl = new ExecutionCommitmentRegistry(address(0));
        registry = ExecutionCommitmentRegistry(
            address(
                new ERC1967Proxy(
                    address(impl), abi.encodeCall(ExecutionCommitmentRegistry.initialize, (owner, dispatcher))
                )
            )
        );
    }

    function _dispatch() internal {
        vm.prank(dispatcher);
        registry.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            crossVerifier,
            uint64(block.timestamp + 10 minutes),
            uint64(block.timestamp + 30 minutes)
        );
    }

    function _digest(IECR.Role role, address node, bytes32 handle, bytes32 salt) internal view returns (bytes32) {
        return registry.commitDigest(role, node, handle, salt);
    }

    function test_dispatch_setsState() public {
        _dispatch();
        IECR.Invocation memory inv = registry.invocation(INVOCATION_ID);
        assertEq(uint8(inv.status), uint8(IECR.Status.DISPATCHED));
        assertEq(inv.executor, executor);
        assertEq(inv.crossVerifier, crossVerifier);
        assertEq(inv.escrowId, ESCROW_ID);
        assertEq(inv.agentId, AGENT_ID);
    }

    function test_dispatch_revertsForNonDispatcher() public {
        vm.expectRevert(IECR.NotDispatcher.selector);
        registry.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            crossVerifier,
            uint64(block.timestamp + 1),
            uint64(block.timestamp + 2)
        );
    }

    function test_dispatch_revertsOnSelfVoting() public {
        vm.prank(dispatcher);
        vm.expectRevert(IECR.SelfVoting.selector);
        registry.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            executor,
            uint64(block.timestamp + 10),
            uint64(block.timestamp + 20)
        );
    }

    function test_dispatch_revertsOnInvalidDeadlines() public {
        vm.startPrank(dispatcher);
        vm.expectRevert(IECR.InvalidDeadlines.selector);
        registry.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            crossVerifier,
            uint64(block.timestamp - 1),
            uint64(block.timestamp + 100)
        );
        vm.expectRevert(IECR.InvalidDeadlines.selector);
        registry.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            crossVerifier,
            uint64(block.timestamp + 100),
            uint64(block.timestamp + 50)
        );
        vm.stopPrank();
    }

    function test_dispatch_revertsOnRedispatch() public {
        _dispatch();
        vm.prank(dispatcher);
        vm.expectRevert(IECR.AlreadyDispatched.selector);
        registry.dispatch(
            INVOCATION_ID,
            ESCROW_ID,
            AGENT_ID,
            executor,
            crossVerifier,
            uint64(block.timestamp + 10),
            uint64(block.timestamp + 20)
        );
    }

    function test_commit_executorThenVerifier_succeeds() public {
        _dispatch();
        bytes32 e = _digest(IECR.Role.EXECUTOR, executor, OUTPUT_HANDLE_OK, SALT_E);
        bytes32 v = _digest(IECR.Role.CROSS_VERIFIER, crossVerifier, OUTPUT_HANDLE_OK, SALT_V);

        vm.prank(executor);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, e);
        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.PARTIAL_COMMIT));

        vm.prank(crossVerifier);
        registry.commit(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, v);
        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.BOTH_COMMITTED));
    }

    function test_commit_revertsForOutsider() public {
        _dispatch();
        bytes32 e = _digest(IECR.Role.EXECUTOR, outsider, OUTPUT_HANDLE_OK, SALT_E);

        vm.prank(outsider);
        vm.expectRevert(IECR.NotExpectedNode.selector);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, e);
    }

    function test_commit_revertsAfterDeadline() public {
        _dispatch();
        skip(20 minutes);

        bytes32 e = _digest(IECR.Role.EXECUTOR, executor, OUTPUT_HANDLE_OK, SALT_E);
        vm.prank(executor);
        vm.expectRevert(IECR.CommitDeadlinePassed.selector);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, e);
    }

    function test_commit_revertsOnDoubleCommit() public {
        _dispatch();
        bytes32 e = _digest(IECR.Role.EXECUTOR, executor, OUTPUT_HANDLE_OK, SALT_E);

        vm.startPrank(executor);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, e);
        vm.expectRevert(IECR.AlreadyCommitted.selector);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, e);
        vm.stopPrank();
    }

    function _bothCommit() internal returns (bytes32 eDig, bytes32 vDig) {
        eDig = _digest(IECR.Role.EXECUTOR, executor, OUTPUT_HANDLE_OK, SALT_E);
        vDig = _digest(IECR.Role.CROSS_VERIFIER, crossVerifier, OUTPUT_HANDLE_OK, SALT_V);

        vm.prank(executor);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, eDig);
        vm.prank(crossVerifier);
        registry.commit(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, vDig);
    }

    function test_reveal_matchingOutputs_transitionsToVerified() public {
        _dispatch();
        _bothCommit();

        vm.prank(executor);
        registry.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, OUTPUT_HANDLE_OK, SALT_E);
        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.PARTIAL_REVEAL));

        vm.expectEmit(true, false, false, true);
        emit IECR.Verified(INVOCATION_ID, OUTPUT_HANDLE_OK);
        vm.prank(crossVerifier);
        registry.reveal(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, OUTPUT_HANDLE_OK, SALT_V);

        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.VERIFIED));
        assertEq(registry.verifiedOutput(INVOCATION_ID), OUTPUT_HANDLE_OK);
    }

    function test_reveal_mismatchedOutputs_transitionsToEscalated() public {
        _dispatch();
        bytes32 eDig = _digest(IECR.Role.EXECUTOR, executor, OUTPUT_HANDLE_OK, SALT_E);
        bytes32 vDig = _digest(IECR.Role.CROSS_VERIFIER, crossVerifier, OUTPUT_HANDLE_BAD, SALT_V);

        vm.prank(executor);
        registry.commit(INVOCATION_ID, IECR.Role.EXECUTOR, eDig);
        vm.prank(crossVerifier);
        registry.commit(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, vDig);

        vm.prank(executor);
        registry.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, OUTPUT_HANDLE_OK, SALT_E);

        vm.expectEmit(true, false, false, true);
        emit IECR.Escalated(INVOCATION_ID, "output mismatch");
        vm.prank(crossVerifier);
        registry.reveal(INVOCATION_ID, IECR.Role.CROSS_VERIFIER, OUTPUT_HANDLE_BAD, SALT_V);

        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.ESCALATED));
        assertEq(registry.verifiedOutput(INVOCATION_ID), bytes32(0));
    }

    function test_reveal_revertsOnForgedSalt() public {
        _dispatch();
        _bothCommit();

        vm.prank(executor);
        vm.expectRevert(IECR.RevealMismatch.selector);
        registry.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, OUTPUT_HANDLE_OK, bytes32(uint256(0xFFFF)));
    }

    function test_reveal_revertsAfterDeadline() public {
        _dispatch();
        _bothCommit();
        skip(40 minutes);

        vm.prank(executor);
        vm.expectRevert(IECR.RevealDeadlinePassed.selector);
        registry.reveal(INVOCATION_ID, IECR.Role.EXECUTOR, OUTPUT_HANDLE_OK, SALT_E);
    }

    function test_markCommitTimeout_escalatesAfterDeadline() public {
        _dispatch();
        skip(20 minutes);

        vm.expectEmit(true, false, false, true);
        emit IECR.Escalated(INVOCATION_ID, "commit timeout");
        registry.markCommitTimeout(INVOCATION_ID);

        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.ESCALATED));
    }

    function test_markCommitTimeout_revertsBeforeDeadline() public {
        _dispatch();
        vm.expectRevert(IECR.CommitDeadlineNotPassed.selector);
        registry.markCommitTimeout(INVOCATION_ID);
    }

    function test_markRevealTimeout_escalatesIfNotVerified() public {
        _dispatch();
        _bothCommit();
        skip(40 minutes);

        registry.markRevealTimeout(INVOCATION_ID);
        assertEq(uint8(registry.statusOf(INVOCATION_ID)), uint8(IECR.Status.ESCALATED));
    }

    function test_setDispatcher_changesAuthorizedAddress() public {
        address newDispatcher = makeAddr("newDispatcher");
        vm.prank(owner);
        registry.setDispatcher(newDispatcher);
        assertEq(registry.dispatcher(), newDispatcher);
    }

    function test_setDispatcher_revertsForNonOwner() public {
        vm.prank(executor);
        vm.expectRevert();
        registry.setDispatcher(makeAddr("x"));
    }

    function test_commitDigest_matchesEncodePacked() public view {
        bytes32 expected = keccak256(abi.encodePacked(uint8(IECR.Role.EXECUTOR), executor, OUTPUT_HANDLE_OK, SALT_E));
        assertEq(_digest(IECR.Role.EXECUTOR, executor, OUTPUT_HANDLE_OK, SALT_E), expected);
    }
}
