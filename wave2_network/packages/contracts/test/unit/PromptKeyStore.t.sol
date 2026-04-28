// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
import {CoFheTest} from "@fhenixprotocol/cofhe-mock-contracts/CoFheTest.sol";
import {PromptKeyStore} from "../../contracts/core/PromptKeyStore.sol";
import {InEuint256, euint256} from "@fhenixprotocol/cofhe-contracts/FHE.sol";

contract PromptKeyStoreTest is Test, CoFheTest {
    PromptKeyStore public store;

    function setUp() public {
        store = new PromptKeyStore();
    }

    function test_storeKey_persistsEncryptedHandles() public {
        bytes32 jobId = keccak256("job-1");
        InEuint256 memory highInput = createInEuint256(111, address(this));
        InEuint256 memory lowInput = createInEuint256(222, address(this));
        address[] memory allowedNodes = new address[](2);
        allowedNodes[0] = makeAddr("leader");
        allowedNodes[1] = makeAddr("verifier");

        store.storeKey(jobId, highInput, lowInput, allowedNodes);

        (euint256 storedHigh, euint256 storedLow) = store.getEncryptedKey(jobId);
        assertTrue(euint256.unwrap(storedHigh) != 0, "high handle should be set");
        assertTrue(euint256.unwrap(storedLow) != 0, "low handle should be set");
    }

    function test_storeKey_overwritesExistingJobKey() public {
        bytes32 jobId = keccak256("job-2");
        address[] memory allowedNodes = new address[](1);
        allowedNodes[0] = makeAddr("leader");

        store.storeKey(jobId, createInEuint256(111, address(this)), createInEuint256(222, address(this)), allowedNodes);
        (euint256 firstHigh, euint256 firstLow) = store.getEncryptedKey(jobId);

        store.storeKey(jobId, createInEuint256(333, address(this)), createInEuint256(444, address(this)), allowedNodes);
        (euint256 secondHigh, euint256 secondLow) = store.getEncryptedKey(jobId);

        assertTrue(euint256.unwrap(firstHigh) != euint256.unwrap(secondHigh), "high handle should update");
        assertTrue(euint256.unwrap(firstLow) != euint256.unwrap(secondLow), "low handle should update");
    }
}
