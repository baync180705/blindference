import crypto from 'crypto'

export interface EncryptedPayload {
  iv: Buffer
  authTag: Buffer
  ciphertext: Buffer
}

export function generateKey(): Buffer {
  return crypto.randomBytes(32)
}

export function encryptText(text: string, key: Buffer): EncryptedPayload {
  if (key.length !== 32) {
    throw new Error('Key must be 32 bytes')
  }

  const iv = crypto.randomBytes(16)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv)
  const ciphertext = Buffer.concat([cipher.update(text, 'utf8'), cipher.final()])
  const authTag = cipher.getAuthTag()

  return { iv, authTag, ciphertext }
}

export function packPayload(payload: EncryptedPayload): Buffer {
  if (payload.iv.length !== 16) {
    throw new Error('IV must be 16 bytes')
  }
  if (payload.authTag.length !== 16) {
    throw new Error('Auth tag must be 16 bytes')
  }

  return Buffer.concat([payload.iv, payload.authTag, payload.ciphertext])
}

export function unpackPayload(packed: Buffer): EncryptedPayload {
  if (packed.length < 32) {
    throw new Error('Packed data too short')
  }

  return {
    iv: packed.subarray(0, 16),
    authTag: packed.subarray(16, 32),
    ciphertext: packed.subarray(32),
  }
}

export function decryptBlob(packed: Buffer, key: Buffer): string {
  if (key.length !== 32) {
    throw new Error('Key must be 32 bytes')
  }

  const { iv, authTag, ciphertext } = unpackPayload(packed)
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv)
  decipher.setAuthTag(authTag)
  const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()])

  return decrypted.toString('utf8')
}

export function splitKeyForFHE(key: Buffer): { high: bigint; low: bigint } {
  if (key.length !== 32) {
    throw new Error('Key must be 32 bytes')
  }

  return {
    high: BigInt(`0x${key.subarray(0, 16).toString('hex')}`),
    low: BigInt(`0x${key.subarray(16, 32).toString('hex')}`),
  }
}

export function combineKeyFromFHE(high: bigint, low: bigint): Buffer {
  const highHex = high.toString(16).padStart(32, '0')
  const lowHex = low.toString(16).padStart(32, '0')

  return Buffer.from(highHex + lowHex, 'hex')
}
