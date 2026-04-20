// SPDX-License-Identifier: BUSL-1.1
pragma solidity ^0.8.28;

import {
    FHE,
    euint8,
    euint32,
    euint64,
    InEuint8,
    InEuint32,
    InEuint64
} from "@fhenixprotocol/cofhe-contracts/FHE.sol";

/// @title BlindferenceInputVault
/// @notice Demo vault that verifies browser-produced CoFHE ciphertexts on-chain and grants the
///         submitting wallet ACL access before node-sharing permits are created.
contract BlindferenceInputVault {
    struct StoredInputs {
        address owner;
        uint64 storedAt;
        euint32 creditScore;
        euint64 loanAmount;
        euint32 accountAge;
        euint8 prevDefaults;
    }

    error EmptyLoanId();
    error LoanOwnedByAnother(address expectedOwner);

    event InputsStored(
        bytes32 indexed loanKey,
        string loanId,
        address indexed owner,
        uint256 creditScoreHandle,
        uint256 loanAmountHandle,
        uint256 accountAgeHandle,
        uint256 prevDefaultsHandle
    );

    mapping(bytes32 loanKey => StoredInputs) private _storedInputs;

    function storeEncryptedInputs(
        string calldata loanId,
        InEuint32 calldata creditScore,
        InEuint64 calldata loanAmount,
        InEuint32 calldata accountAge,
        InEuint8 calldata prevDefaults
    ) external returns (bytes32 loanKey) {
        if (bytes(loanId).length == 0) {
            revert EmptyLoanId();
        }

        loanKey = keccak256(bytes(loanId));
        StoredInputs storage current = _storedInputs[loanKey];
        if (current.owner != address(0) && current.owner != msg.sender) {
            revert LoanOwnedByAnother(current.owner);
        }

        euint32 creditScoreHandle = FHE.asEuint32(creditScore);
        euint64 loanAmountHandle = FHE.asEuint64(loanAmount);
        euint32 accountAgeHandle = FHE.asEuint32(accountAge);
        euint8 prevDefaultsHandle = FHE.asEuint8(prevDefaults);

        _grantAccess(creditScoreHandle, msg.sender);
        _grantAccess(loanAmountHandle, msg.sender);
        _grantAccess(accountAgeHandle, msg.sender);
        _grantAccess(prevDefaultsHandle, msg.sender);

        current.owner = msg.sender;
        current.storedAt = uint64(block.timestamp);
        current.creditScore = creditScoreHandle;
        current.loanAmount = loanAmountHandle;
        current.accountAge = accountAgeHandle;
        current.prevDefaults = prevDefaultsHandle;

        emit InputsStored(
            loanKey,
            loanId,
            msg.sender,
            euint32.unwrap(creditScoreHandle),
            euint64.unwrap(loanAmountHandle),
            euint32.unwrap(accountAgeHandle),
            euint8.unwrap(prevDefaultsHandle)
        );
    }

    function storedInputHandles(string calldata loanId)
        external
        view
        returns (
            address owner,
            uint64 storedAt,
            uint256 creditScoreHandle,
            uint256 loanAmountHandle,
            uint256 accountAgeHandle,
            uint256 prevDefaultsHandle
        )
    {
        StoredInputs storage current = _storedInputs[keccak256(bytes(loanId))];
        return (
            current.owner,
            current.storedAt,
            euint32.unwrap(current.creditScore),
            euint64.unwrap(current.loanAmount),
            euint32.unwrap(current.accountAge),
            euint8.unwrap(current.prevDefaults)
        );
    }

    function _grantAccess(euint32 handle, address owner) internal {
        FHE.allowThis(handle);
        FHE.allow(handle, owner);
    }

    function _grantAccess(euint64 handle, address owner) internal {
        FHE.allowThis(handle);
        FHE.allow(handle, owner);
    }

    function _grantAccess(euint8 handle, address owner) internal {
        FHE.allowThis(handle);
        FHE.allow(handle, owner);
    }
}
