// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.25;

import {Test, Vm} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import {NodeAttestationRegistry} from "../../contracts/core/NodeAttestationRegistry.sol";
import {INodeAttestationRegistry} from "../../contracts/interfaces/core/INodeAttestationRegistry.sol";

contract NodeAttestationRegistryTest is Test {
    using MessageHashUtils for bytes32;

    NodeAttestationRegistry public registry;

    address public owner = makeAddr("owner");
    Vm.Wallet public node;
    Vm.Wallet public otherNode;

    bytes32 public constant ZDR = keccak256("zdr.v1");
    bytes32 public constant HIPAA = keccak256("hipaa-baa.v1");
    bytes32 public constant DOC_HASH = keccak256("policy-document-v1");

    function setUp() public {
        node = vm.createWallet("node");
        otherNode = vm.createWallet("otherNode");

        NodeAttestationRegistry impl = new NodeAttestationRegistry(address(0));
        registry = NodeAttestationRegistry(
            address(new ERC1967Proxy(address(impl), abi.encodeCall(NodeAttestationRegistry.initialize, (owner))))
        );
    }

    function _sign(
        Vm.Wallet memory signer,
        address nodeAddr,
        bytes32 attestationType,
        bytes32 documentHash,
        address counterparty,
        uint64 effectiveAt,
        uint64 expiresAt
    ) internal view returns (bytes memory) {
        bytes32 d = registry.digest(nodeAddr, attestationType, documentHash, counterparty, effectiveAt, expiresAt);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signer.privateKey, d.toEthSignedMessageHash());
        return abi.encodePacked(r, s, v);
    }

    function test_commit_storesPublicAttestation() public {
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;

        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);

        assertTrue(registry.hasValid(node.addr, ZDR, address(0)));

        INodeAttestationRegistry.Attestation memory a = registry.attestationOf(node.addr, ZDR, address(0));
        assertEq(a.documentHash, DOC_HASH);
        assertEq(a.counterparty, address(0));
        assertFalse(a.revoked);
    }

    function test_commit_emitsEvent() public {
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        vm.expectEmit(true, true, true, true);
        emit INodeAttestationRegistry.AttestationCommitted(node.addr, ZDR, address(0), DOC_HASH, effectiveAt, expiresAt);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);
    }

    function test_commit_supportsBilateralAttestation() public {
        address counterparty = makeAddr("riskAgent");
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;

        bytes memory sig = _sign(node, node.addr, HIPAA, DOC_HASH, counterparty, effectiveAt, expiresAt);
        registry.commit(node.addr, HIPAA, DOC_HASH, counterparty, effectiveAt, expiresAt, sig);

        assertTrue(registry.hasValid(node.addr, HIPAA, counterparty));
        assertFalse(registry.hasValid(node.addr, HIPAA, address(0)));
    }

    function test_commit_revertsOnSignatureFromWrongKey() public {
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;

        bytes memory wrongSig = _sign(otherNode, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        vm.expectRevert(INodeAttestationRegistry.InvalidSignature.selector);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, wrongSig);
    }

    function test_commit_revertsOnZeroEffectiveAt() public {
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), 0, 1);
        vm.expectRevert(INodeAttestationRegistry.InvalidWindow.selector);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), 0, 1, sig);
    }

    function test_commit_revertsWhenExpiresBeforeEffective() public {
        uint64 effectiveAt = uint64(block.timestamp + 100);
        uint64 expiresAt = effectiveAt - 1;
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        vm.expectRevert(INodeAttestationRegistry.InvalidWindow.selector);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);
    }

    function test_commit_revertsWhenAlreadyExpired() public {
        skip(1000);
        uint64 effectiveAt = uint64(block.timestamp - 500);
        uint64 expiresAt = uint64(block.timestamp - 1);
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        vm.expectRevert(INodeAttestationRegistry.AttestationExpired.selector);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);
    }

    function test_hasValid_falseBeforeEffectiveAt() public {
        uint64 effectiveAt = uint64(block.timestamp + 1 days);
        uint64 expiresAt = effectiveAt + 365 days;
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);

        assertFalse(registry.hasValid(node.addr, ZDR, address(0)));
        skip(2 days);
        assertTrue(registry.hasValid(node.addr, ZDR, address(0)));
    }

    function test_hasValid_falseAfterExpiry() public {
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 1 days;
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);
        assertTrue(registry.hasValid(node.addr, ZDR, address(0)));
        skip(2 days);
        assertFalse(registry.hasValid(node.addr, ZDR, address(0)));
    }

    function test_revoke_marksRevokedAndInvalidates() public {
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;
        bytes memory sig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);

        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig);
        assertTrue(registry.hasValid(node.addr, ZDR, address(0)));

        vm.expectEmit(true, true, true, false);
        emit INodeAttestationRegistry.AttestationRevoked(node.addr, ZDR, address(0));
        vm.prank(node.addr);
        registry.revoke(ZDR, address(0));

        assertFalse(registry.hasValid(node.addr, ZDR, address(0)));
    }

    function test_revoke_revertsOnUnknownAttestation() public {
        vm.prank(node.addr);
        vm.expectRevert(INodeAttestationRegistry.AttestationNotFound.selector);
        registry.revoke(ZDR, address(0));
    }

    function test_recommit_overwritesPrior() public {
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;
        bytes memory sig1 = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, sig1);

        bytes32 newDoc = keccak256("policy-v2");
        uint64 newExpiry = effectiveAt + 730 days;
        bytes memory sig2 = _sign(node, node.addr, ZDR, newDoc, address(0), effectiveAt, newExpiry);
        registry.commit(node.addr, ZDR, newDoc, address(0), effectiveAt, newExpiry, sig2);

        INodeAttestationRegistry.Attestation memory stored = registry.attestationOf(node.addr, ZDR, address(0));
        assertEq(stored.documentHash, newDoc);
        assertEq(stored.expiresAt, newExpiry);
    }

    function test_publicAndBilateral_areIndependent() public {
        address counterparty = makeAddr("agent");
        uint64 effectiveAt = uint64(block.timestamp);
        uint64 expiresAt = effectiveAt + 365 days;

        bytes memory pubSig = _sign(node, node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt);
        registry.commit(node.addr, ZDR, DOC_HASH, address(0), effectiveAt, expiresAt, pubSig);

        bytes memory bilSig = _sign(node, node.addr, ZDR, DOC_HASH, counterparty, effectiveAt, expiresAt);
        registry.commit(node.addr, ZDR, DOC_HASH, counterparty, effectiveAt, expiresAt, bilSig);

        assertTrue(registry.hasValid(node.addr, ZDR, address(0)));
        assertTrue(registry.hasValid(node.addr, ZDR, counterparty));

        vm.prank(node.addr);
        registry.revoke(ZDR, address(0));

        assertFalse(registry.hasValid(node.addr, ZDR, address(0)));
        assertTrue(registry.hasValid(node.addr, ZDR, counterparty));
    }
}
