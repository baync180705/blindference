import lighthouse from '@lighthouse-web3/sdk'

function getApiKey(): string {
  const apiKey = process.env.LIGHTHOUSE_API_KEY
  if (!apiKey) {
    throw new Error('LIGHTHOUSE_API_KEY is not set')
  }
  return apiKey
}

export async function uploadToIPFS(data: Buffer): Promise<string> {
  const response = await lighthouse.uploadBuffer(data, getApiKey())

  if (!response.data?.Hash) {
    throw new Error(`IPFS upload failed: ${JSON.stringify(response)}`)
  }

  return response.data.Hash
}

export async function downloadFromIPFS(cid: string): Promise<Buffer> {
  const url = `https://gateway.lighthouse.storage/ipfs/${cid}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`IPFS download failed: ${response.status} ${response.statusText}`)
  }

  const arrayBuffer = await response.arrayBuffer()
  return Buffer.from(arrayBuffer)
}
