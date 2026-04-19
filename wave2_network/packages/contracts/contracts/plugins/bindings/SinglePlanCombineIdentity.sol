// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {ERC165} from "@openzeppelin/contracts/utils/introspection/ERC165.sol";
import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {IAgentPolicy} from "../../interfaces/plugins/IAgentPolicy.sol";
import {IModelBinding} from "../../interfaces/plugins/IModelBinding.sol";

contract SinglePlanCombineIdentity is ERC165, IAgentPolicy {
    IModelBinding public immutable BINDING;

    error ExpectsExactlyOneOutput();

    constructor(IModelBinding binding_) {
        BINDING = binding_;
    }

    function plan(bytes calldata) external view returns (IModelBinding[] memory ordered) {
        ordered = new IModelBinding[](1);
        ordered[0] = BINDING;
    }

    function combine(bytes[] calldata modelOutputs) external pure returns (bytes memory) {
        if (modelOutputs.length != 1) {
            revert ExpectsExactlyOneOutput();
        }
        return modelOutputs[0];
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC165, IERC165) returns (bool) {
        return interfaceId == type(IAgentPolicy).interfaceId || super.supportsInterface(interfaceId);
    }
}
