// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {ERC165} from "@openzeppelin/contracts/utils/introspection/ERC165.sol";
import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {IQuorumPolicy} from "../../interfaces/plugins/IQuorumPolicy.sol";

contract FixedQuorumPolicy is ERC165, IQuorumPolicy {
    bytes32 public immutable QUORUM_ID;

    error ZeroQuorumId();

    constructor(bytes32 quorumId_) {
        if (quorumId_ == bytes32(0)) {
            revert ZeroQuorumId();
        }
        QUORUM_ID = quorumId_;
    }

    function selectQuorum(uint256, bytes calldata) external view returns (bytes32) {
        return QUORUM_ID;
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC165, IERC165) returns (bool) {
        return interfaceId == type(IQuorumPolicy).interfaceId || super.supportsInterface(interfaceId);
    }
}
