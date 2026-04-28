// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

import {FHE, InEuint256, euint256} from "@fhenixprotocol/cofhe-contracts/FHE.sol";

/// @title PromptKeyStore
/// @notice Stores CoFHE-encrypted AES prompt-key halves and grants assigned nodes ACL access.
contract PromptKeyStore {
    struct StoredKey {
        euint256 high;
        euint256 low;
    }

    mapping(bytes32 jobId => StoredKey) private _jobKeys;

    event KeyStored(
        bytes32 indexed jobId,
        address indexed submitter,
        uint256 highHandle,
        uint256 lowHandle,
        address[] allowedNodes
    );

    function storeKey(
        bytes32 jobId,
        InEuint256 calldata encHigh,
        InEuint256 calldata encLow,
        address[] calldata allowedNodes
    ) external {
        euint256 high = FHE.asEuint256(encHigh);
        euint256 low = FHE.asEuint256(encLow);

        _grantAccess(high, allowedNodes);
        _grantAccess(low, allowedNodes);

        _jobKeys[jobId] = StoredKey({high: high, low: low});

        emit KeyStored(jobId, msg.sender, euint256.unwrap(high), euint256.unwrap(low), allowedNodes);
    }

    function getEncryptedKey(bytes32 jobId) external view returns (euint256, euint256) {
        StoredKey storage key = _jobKeys[jobId];
        return (key.high, key.low);
    }

    function _grantAccess(euint256 handle, address[] calldata allowedNodes) internal {
        FHE.allowThis(handle);
        for (uint256 index = 0; index < allowedNodes.length; index++) {
            FHE.allow(handle, allowedNodes[index]);
        }
    }
}
