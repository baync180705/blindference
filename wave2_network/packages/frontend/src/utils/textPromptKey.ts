import { type CofheClient, type EncryptedItemInput } from '../lib/cofhe'

type SerializedEncryptedInput = {
  ctHash: string
  securityZone: number
  utype: number
  signature: string
}

export type EncryptedPromptKeyPayload = {
  encryptedPromptKey: {
    high: string
    low: string
  }
  metadata: {
    cofhe_prompt_key_inputs: {
      high: SerializedEncryptedInput
      low: SerializedEncryptedInput
    }
  }
}

export async function encryptPromptKeyForTextRequest(
  client: CofheClient,
  promptKey: Uint8Array,
): Promise<EncryptedPromptKeyPayload> {
  if (promptKey.byteLength !== 32) {
    throw new Error(`Prompt key must be 32 bytes, received ${promptKey.byteLength}`)
  }

  const high = bigintFromBytes(promptKey.subarray(0, 16))
  const low = bigintFromBytes(promptKey.subarray(16, 32))
  const [highInput, lowInput] = await client
    .encryptInputs([
      u256Encryptable(high),
      u256Encryptable(low),
    ] as any)
    .execute()

  return {
    encryptedPromptKey: {
      high: highInput.ctHash.toString(),
      low: lowInput.ctHash.toString(),
    },
    metadata: {
      cofhe_prompt_key_inputs: {
        high: serializeEncryptedInput(highInput),
        low: serializeEncryptedInput(lowInput),
      },
    },
  }
}

export async function decryptOutputKey(
  client: CofheClient,
  highHandle: string,
  lowHandle: string,
): Promise<Uint8Array> {
  const permit = await client.permits.getOrCreateSelfPermit()
  const high = await client.decryptForView(highHandle, 8).withPermit(permit).execute()
  const low = await client.decryptForView(lowHandle, 8).withPermit(permit).execute()
  return combineUint256Halves(high, low)
}

export async function downloadAndDecryptTextOutput(
  outputCid: string,
  key: Uint8Array,
): Promise<string> {
  const response = await fetch(`https://gateway.lighthouse.storage/ipfs/${outputCid}`)
  if (!response.ok) {
    throw new Error(`Failed to download encrypted output from IPFS: ${response.statusText}`)
  }

  const packed = new Uint8Array(await response.arrayBuffer())
  if (packed.byteLength < 32) {
    throw new Error('Encrypted output payload is too short')
  }

  const iv = packed.subarray(0, 16)
  const authTag = packed.subarray(16, 32)
  const ciphertext = packed.subarray(32)
  const cipherWithTag = new Uint8Array(ciphertext.length + authTag.length)
  cipherWithTag.set(ciphertext)
  cipherWithTag.set(authTag, ciphertext.length)

  const cryptoKey = await crypto.subtle.importKey('raw', key, 'AES-GCM', false, ['decrypt'])
  const plaintext = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv, tagLength: 128 },
    cryptoKey,
    cipherWithTag,
  )

  return new TextDecoder().decode(plaintext)
}

function serializeEncryptedInput(input: EncryptedItemInput): SerializedEncryptedInput {
  return {
    ctHash: input.ctHash.toString(),
    securityZone: input.securityZone,
    utype: Number(input.utype),
    signature: input.signature,
  }
}

function bigintFromBytes(bytes: Uint8Array): bigint {
  let value = 0n
  for (const byte of bytes) {
    value = (value << 8n) | BigInt(byte)
  }
  return value
}

function combineUint256Halves(high: bigint, low: bigint): Uint8Array {
  const output = new Uint8Array(32)
  writeBigIntToBytes(high, output, 0)
  writeBigIntToBytes(low, output, 16)
  return output
}

function u256Encryptable(value: bigint) {
  return {
    data: value,
    securityZone: 0,
    utype: 8,
  }
}

function writeBigIntToBytes(value: bigint, output: Uint8Array, offset: number) {
  let remaining = value
  for (let index = 15; index >= 0; index -= 1) {
    output[offset + index] = Number(remaining & 0xffn)
    remaining >>= 8n
  }
}
