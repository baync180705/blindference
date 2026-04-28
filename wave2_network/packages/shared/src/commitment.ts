import crypto from 'crypto'

export function hashOutput(text: string): Buffer {
  return crypto.createHash('sha256').update(text, 'utf8').digest()
}

export function buildCommitmentHash(outputCID: string, outputHash: Buffer): string {
  return crypto.createHash('sha256').update(Buffer.concat([Buffer.from(outputCID, 'utf8'), outputHash])).digest('hex')
}
