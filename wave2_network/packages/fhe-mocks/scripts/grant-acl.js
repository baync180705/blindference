const hre = require('hardhat')

async function main() {
  const ctHash = process.env.CT_HASH
  const operator = process.env.OPERATOR_ADDRESS
  const requester = process.env.REQUESTER_ADDRESS || operator

  if (!ctHash || !operator) {
    throw new Error('Set CT_HASH and OPERATOR_ADDRESS before running grant-acl')
  }

  const taskManager = await hre.cofhe.mocks.getMockTaskManager()
  const signer = await hre.ethers.getSigner(requester)

  await taskManager.connect(signer).allow(ctHash, operator)

  console.log(`Granted ACL access for ${operator} on ${ctHash}`)
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
