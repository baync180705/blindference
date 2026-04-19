// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.28;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @notice Lightweight metadata anchor for the Blindference demo vertical.
/// The core protocol registries remain the execution source of truth; this
/// contract gives the demo a branded on-chain identity with stable pointers to
/// the attestor and underwriter seams.
contract BlindferenceAgent is Ownable {
    string public name;
    string public provider;
    string public modelIdentifier;
    address public attestor;
    address public underwriter;

    event MetadataUpdated(string provider, string modelIdentifier);
    event ContractsUpdated(address indexed attestor, address indexed underwriter);

    constructor(
        address owner_,
        string memory name_,
        string memory provider_,
        string memory modelIdentifier_,
        address attestor_,
        address underwriter_
    ) Ownable(owner_) {
        name = name_;
        provider = provider_;
        modelIdentifier = modelIdentifier_;
        attestor = attestor_;
        underwriter = underwriter_;
    }

    function setMetadata(string calldata provider_, string calldata modelIdentifier_) external onlyOwner {
        provider = provider_;
        modelIdentifier = modelIdentifier_;
        emit MetadataUpdated(provider_, modelIdentifier_);
    }

    function setContracts(address attestor_, address underwriter_) external onlyOwner {
        attestor = attestor_;
        underwriter = underwriter_;
        emit ContractsUpdated(attestor_, underwriter_);
    }
}
