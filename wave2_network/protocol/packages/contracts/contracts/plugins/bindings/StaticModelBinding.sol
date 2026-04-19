// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {ERC165} from "@openzeppelin/contracts/utils/introspection/ERC165.sol";
import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {IModelBinding} from "../../interfaces/plugins/IModelBinding.sol";
import {PricingConfig} from "../../common/Types.sol";

contract StaticModelBinding is ERC165, IModelBinding {
    uint256 private immutable _MODEL_ID;
    uint8 private immutable _QUORUM_SIZE;
    PricingConfig private _pricing;

    error ZeroModelId();

    constructor(uint256 modelId_, uint8 quorumSize_, PricingConfig memory pricing_) {
        if (modelId_ == 0) {
            revert ZeroModelId();
        }
        _MODEL_ID = modelId_;
        _QUORUM_SIZE = quorumSize_;
        _pricing = pricing_;
    }

    function modelId() external view returns (uint256) {
        return _MODEL_ID;
    }

    function pricing() external view returns (PricingConfig memory) {
        return _pricing;
    }

    function requiredQuorumSize() external view returns (uint8) {
        return _QUORUM_SIZE;
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC165, IERC165) returns (bool) {
        return interfaceId == type(IModelBinding).interfaceId || super.supportsInterface(interfaceId);
    }
}
