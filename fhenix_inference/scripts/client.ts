import * as dotenv from "dotenv";
import { ethers } from "hardhat";
import hre from "hardhat";

dotenv.config();

async function main() {
  const contractAddress = process.env.BLIND_INFERENCE_ADDRESS;
  if (!contractAddress) {
    throw new Error("BLIND_INFERENCE_ADDRESS is not set");
  }

  const [user] = await ethers.getSigners();
  const contract = await ethers.getContractAt("BlindInference", contractAddress, user);

  const scaledGlucose = 115;
  const scaledBmi = 133;

  const encryptedFeatures = await Promise.all([
    hre.fhenixjs.encrypt_uint32(scaledGlucose),
    hre.fhenixjs.encrypt_uint32(scaledBmi),
  ]);

  const tx = await contract.predict(encryptedFeatures);
  const receipt = await tx.wait();

  const permit = await hre.fhenixjs.createPermit(contractAddress);
  const sealedPrediction = await contract.getMyPrediction(permit.publicKey);
  const unsealedPrediction = await hre.fhenixjs.unseal(
    contractAddress,
    sealedPrediction,
  );

  console.log("Prediction transaction mined");
  console.log(`User: ${user.address}`);
  console.log(`Tx hash: ${receipt?.hash ?? "unknown"}`);
  console.log(`Scaled inputs: glucose=${scaledGlucose}, bmi=${scaledBmi}`);
  console.log(`Predicted positive class: ${Boolean(unsealedPrediction)}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
