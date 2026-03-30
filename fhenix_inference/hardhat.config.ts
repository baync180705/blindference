import * as dotenv from "dotenv";
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-ethers";
import "fhenix-hardhat-plugin";
import "fhenix-hardhat-docker";
import "fhenix-hardhat-network";

dotenv.config();

const accounts = process.env.DEPLOYER_PRIVATE_KEY
  ? [process.env.DEPLOYER_PRIVATE_KEY]
  : [];

const config: HardhatUserConfig = {
  solidity: "0.8.24",
  networks: {
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL ?? "",
      chainId: 11155111,
      accounts,
    },
  },
};

export default config;
