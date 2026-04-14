import hre from "hardhat";

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Contracts deploy stub ready for:", deployer.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
