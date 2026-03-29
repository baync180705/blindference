type FhenixClientLike = {
  encrypt_uint32(value: number): Promise<{ data: Uint8Array; securityZone: number }>;
};

export interface Model {
  id: string;
  name: string;
  price: number;
  labAddress: string;
  accuracy: string;
}

export const MOCK_MODELS: Model[] = [
  { id: "MOD-001", name: "Diabetes Risk V2", price: 5.5, labAddress: "0x71C...3A1", accuracy: "94.2%" },
  { id: "MOD-002", name: "CardioScan Pro", price: 12.0, labAddress: "0x92B...4F2", accuracy: "91.8%" },
  { id: "MOD-003", name: "NeuroDetect Alpha", price: 25.0, labAddress: "0xA5E...9D0", accuracy: "89.5%" },
];

export const sleep = (ms: number) => new globalThis.Promise(resolve => setTimeout(resolve, ms));
export type EncryptedInferenceInput = Awaited<ReturnType<FhenixClientLike['encrypt_uint32']>>;

export function assertUint32(value: number): number {
  if (!Number.isFinite(value) || value < 0 || value > 0xffff_ffff) {
    throw new Error('Inference inputs must be finite uint32 values');
  }
  return Math.trunc(value);
}

export async function encryptInferenceInput(
  client: FhenixClientLike,
  value: number,
): Promise<EncryptedInferenceInput> {
  return client.encrypt_uint32(assertUint32(value));
}

export async function encrypt_uint32(value: number): Promise<string>;
export async function encrypt_uint32(
  client: FhenixClientLike,
  value: number,
): Promise<EncryptedInferenceInput>;
export async function encrypt_uint32(
  clientOrValue: FhenixClientLike | number,
  maybeValue?: number,
): Promise<EncryptedInferenceInput | string> {
  if (typeof clientOrValue === 'number') {
    const value = assertUint32(clientOrValue);
    await sleep(10);
    return `0xENC_${value.toString(16).padStart(8, '0')}`;
  }

  return encryptInferenceInput(clientOrValue, maybeValue ?? 0);
}

export async function mockDecrypt(handle: string) {
  await sleep(1500);
  const result = Math.random() > 0.5 ? "High Risk Detected" : "Low Risk Detected";
  return result;
}
