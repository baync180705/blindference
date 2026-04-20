import { parseAbi, type Hex, type PublicClient, type WalletClient } from 'viem'

import type { EncryptedItemInput } from './cofhe'

export const blindferenceInputVaultAbi = parseAbi([
  'function storeEncryptedInputs(string loanId, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) creditScore, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) loanAmount, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) accountAge, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) prevDefaults) returns (bytes32 loanKey)',
  'function storedInputHandles(string loanId) view returns (address owner, uint64 storedAt, uint256 creditScoreHandle, uint256 loanAmountHandle, uint256 accountAgeHandle, uint256 prevDefaultsHandle)',
])

type StoreEncryptedRiskInputsArgs = {
  encryptedInputs: EncryptedItemInput[]
  loanId: string
  publicClient: PublicClient
  vaultAddress: Hex
  walletClient: WalletClient
}

type StoredVaultInputs = {
  owner: Hex
  storedAt: bigint
  handles: [bigint, bigint, bigint, bigint]
}

export async function storeEncryptedRiskInputsInVault({
  encryptedInputs,
  loanId,
  publicClient,
  vaultAddress,
  walletClient,
}: StoreEncryptedRiskInputsArgs): Promise<Hex> {
  if (!walletClient.account) {
    throw new Error('Wallet client is missing the active account.')
  }

  if (encryptedInputs.length !== 4) {
    throw new Error(`BlindferenceInputVault expects exactly 4 encrypted features, got ${encryptedInputs.length}.`)
  }

  const [creditScore, loanAmount, accountAge, prevDefaults] = encryptedInputs
  const toContractInput = (item: EncryptedItemInput) => ({
    ctHash: item.ctHash,
    securityZone: item.securityZone ?? 0,
    utype: Number(item.utype),
    signature: item.signature as Hex,
  })

  const latestBlock = await publicClient.getBlock({ blockTag: 'latest' })
  const fallbackPriorityFeePerGas = 2_000_000n
  const maxPriorityFeePerGas = await publicClient
    .estimateMaxPriorityFeePerGas()
    .catch(() => fallbackPriorityFeePerGas)
  const priorityFeePerGas = maxPriorityFeePerGas > 0n ? maxPriorityFeePerGas : fallbackPriorityFeePerGas
  const baseFeePerGas = latestBlock.baseFeePerGas
  const feeParams =
    baseFeePerGas != null
      ? {
          maxPriorityFeePerGas: priorityFeePerGas,
          // Add a small buffer above the current base fee to avoid race-condition underpricing.
          maxFeePerGas: baseFeePerGas * 2n + priorityFeePerGas + 1_000_000n,
        }
      : {
          gasPrice: await publicClient.getGasPrice(),
        }

  const hash = await walletClient.writeContract({
    account: walletClient.account,
    address: vaultAddress,
    abi: blindferenceInputVaultAbi,
    chain: walletClient.chain,
    functionName: 'storeEncryptedInputs',
    args: [
      loanId,
      toContractInput(creditScore),
      toContractInput(loanAmount),
      toContractInput(accountAge),
      toContractInput(prevDefaults),
    ],
    ...feeParams,
  })

  const receipt = await publicClient.waitForTransactionReceipt({ hash })
  if (receipt.status !== 'success') {
    throw new Error(`Input vault transaction failed for loan ${loanId}.`)
  }

  return hash
}

export async function readStoredRiskInputHandles({
  loanId,
  publicClient,
  vaultAddress,
}: {
  loanId: string
  publicClient: PublicClient
  vaultAddress: Hex
}): Promise<StoredVaultInputs> {
  const storedInputs = (await publicClient.readContract({
      address: vaultAddress,
      abi: blindferenceInputVaultAbi,
      functionName: 'storedInputHandles',
      args: [loanId],
    } as never)) as [Hex, bigint, bigint, bigint, bigint, bigint]
  const [owner, storedAt, creditScoreHandle, loanAmountHandle, accountAgeHandle, prevDefaultsHandle] =
    storedInputs

  return {
    owner,
    storedAt,
    handles: [creditScoreHandle, loanAmountHandle, accountAgeHandle, prevDefaultsHandle],
  }
}
