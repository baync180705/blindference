import { Encryptable, type CofheClient, type EncryptedItemInput } from '../lib/cofhe'

export async function encryptRiskFeatures(
  client: CofheClient,
  features: {
    creditScore: number
    loanAmount: number
    accountAge: number
    prevDefaults: number
  },
): Promise<EncryptedItemInput[]> {
  return client
    .encryptInputs([
      Encryptable.uint32(BigInt(features.creditScore)),
      Encryptable.uint64(BigInt(features.loanAmount)),
      Encryptable.uint32(BigInt(features.accountAge)),
      Encryptable.uint8(BigInt(features.prevDefaults)),
    ])
    .execute()
}
