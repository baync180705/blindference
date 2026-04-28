// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";

import {PromptKeyStore} from "../contracts/core/PromptKeyStore.sol";

contract DeployPromptKeyStore is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);
        PromptKeyStore keyStore = new PromptKeyStore();
        vm.stopBroadcast();

        console2.log("PromptKeyStore deployed at:", address(keyStore));
    }
}
