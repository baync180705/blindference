import { createCofheClient, createCofheConfig } from '@cofhe/sdk/node'
import { FheTypes } from '@cofhe/sdk'
import { chains } from '@cofhe/sdk/chains'
import { createPublicClient, createWalletClient, http } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { arbitrumSepolia, hardhat } from 'viem/chains'

function parseJsonInput() {
  return new Promise((resolve, reject) => {
    let source = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', (chunk) => {
      source += chunk
    })
    process.stdin.on('end', () => {
      try {
        resolve(JSON.parse(source || '{}'))
      } catch (error) {
        reject(error)
      }
    })
    process.stdin.on('error', reject)
  })
}

function resolveChains(chainId) {
  if (Number(chainId) === 31337) {
    return {
      cofheChain: chains.hardhat,
      viemChain: hardhat,
    }
  }

  return {
    cofheChain: chains.arbSepolia,
    viemChain: arbitrumSepolia,
  }
}

function resolveFheType(utype) {
  if (typeof utype === 'number') return utype

  const normalized = String(utype).toLowerCase()
  const mapping = {
    bool: FheTypes.Bool,
    uint8: FheTypes.Uint8,
    uint16: FheTypes.Uint16,
    uint32: FheTypes.Uint32,
    uint64: FheTypes.Uint64,
    uint128: FheTypes.Uint128,
    uint160: FheTypes.Uint160,
    address: FheTypes.Uint160,
  }

  if (!(normalized in mapping)) {
    throw new Error(`Unsupported FHE type: ${utype}`)
  }

  return mapping[normalized]
}

async function createClient({ rpcUrl, privateKey, chainId }) {
  const { cofheChain, viemChain } = resolveChains(chainId)
  const config = createCofheConfig({
    supportedChains: [cofheChain],
  })
  const client = createCofheClient(config)
  const account = privateKeyToAccount(privateKey)
  const publicClient = createPublicClient({
    chain: viemChain,
    transport: http(rpcUrl),
  })
  const walletClient = createWalletClient({
    account,
    chain: viemChain,
    transport: http(rpcUrl),
  })

  await client.connect(publicClient, walletClient)
  return { client, publicClient, walletClient, account }
}

async function decryptForView(payload) {
  const { client, publicClient, walletClient } = await createClient(payload)

  if (!payload.permit) {
    throw new Error('Missing shared permit for decryption')
  }

  await client.permits.importShared(payload.permit, { publicClient, walletClient })
  const values = []

  for (const feature of payload.features ?? []) {
    const unsealed = await client
      .decryptForView(BigInt(feature.ctHash), resolveFheType(feature.utype))
      .withPermit()
      .execute()
    values.push(unsealed.toString())
  }

  return { values }
}

async function createSharingPermit(payload) {
  const { client, publicClient, walletClient, account } = await createClient(payload)
  const permit = await client.permits.createSharing(
    {
      issuer: payload.issuer || account.address,
      recipient: payload.recipient,
      name: payload.name || 'Blindference Shared Permit',
    },
    { publicClient, walletClient },
  )

  return {
    permit: client.permits.serialize(permit),
  }
}

async function main() {
  try {
    const payload = await parseJsonInput()
    let result

    switch (payload.action) {
      case 'decrypt_for_view':
        result = await decryptForView(payload)
        break
      case 'create_sharing_permit':
        result = await createSharingPermit(payload)
        break
      default:
        throw new Error(`Unsupported action: ${payload.action}`)
    }

    process.stdout.write(`${JSON.stringify({ ok: true, ...result })}\n`)
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.stack || error.message : String(error)}\n`)
    process.stdout.write(`${JSON.stringify({ ok: false, error: error instanceof Error ? error.message : String(error) })}\n`)
    process.exitCode = 1
  }
}

await main()
