import { Encryptable, FheTypes, type CofheClient, type EncryptedUint32Input } from '@cofhe/sdk';
import type { Contract, ContractTransactionReceipt } from 'ethers';
import { parseUnits } from 'ethers';

export interface Model {
  id: string;
  modelId?: bigint;
  name: string;
  price: number;
  labAddress: string;
  accuracy: string;
}

export interface MockLogisticRegressionModel {
  name: string;
  scale: number;
  features: string[];
  weights: number[];
  bias: number;
  ipfsHash: string;
}

export interface RegisteredModelReceipt {
  modelId: bigint;
  receipt: ContractTransactionReceipt;
}

export interface InferenceSubmission {
  requestId: bigint;
  receipt: ContractTransactionReceipt;
}

export const MOCK_MODELS: Model[] = [
  { id: 'MOD-001', name: 'Diabetes Risk V2', price: 5.5, labAddress: '0x71C...3A1', accuracy: '94.2%' },
  { id: 'MOD-002', name: 'CardioScan Pro', price: 12.0, labAddress: '0x92B...4F2', accuracy: '91.8%' },
  { id: 'MOD-003', name: 'NeuroDetect Alpha', price: 25.0, labAddress: '0xA5E...9D0', accuracy: '89.5%' },
];

export type EncryptedInferenceInput = EncryptedUint32Input;

export function assertUint32(value: number): number {
  if (!Number.isFinite(value) || value < 0 || value > 0xffff_ffff) {
    throw new Error('Inference inputs must be finite uint32 values');
  }
  return Math.trunc(value);
}

export function createMockDiabetesModel(): MockLogisticRegressionModel {
  return {
    name: 'Diabetes-LogReg',
    scale: 1000,
    features: ['Glucose', 'BMI', 'Age'],
    weights: [150, 210, 55],
    bias: 500,
    ipfsHash: 'blindference://diabetes-logreg-v1',
  };
}

export async function encryptUint32(
  client: CofheClient,
  value: number,
): Promise<EncryptedInferenceInput> {
  const [encryptedInput] = await client
    .encryptInputs([Encryptable.uint32(BigInt(assertUint32(value)))])
    .execute();
  return encryptedInput;
}

export async function encryptUint32Array(
  client: CofheClient,
  values: number[],
): Promise<EncryptedInferenceInput[]> {
  const encryptables = values.map((value) => Encryptable.uint32(BigInt(assertUint32(value))));
  return client.encryptInputs(encryptables).execute();
}

export async function encryptInferenceInput(
  client: CofheClient,
  value: number,
): Promise<EncryptedInferenceInput> {
  return encryptUint32(client, value);
}

export async function ensureSelfPermit(client: CofheClient, issuer: `0x${string}`) {
  const permit = await client.permits.getOrCreateSelfPermit(undefined, undefined, {
    issuer,
    name: 'Blindference result permit',
  });
  const permitHash = client.permits.getHash(permit);
  client.permits.selectActivePermit(permitHash);
  return permit;
}

export async function decryptInferenceResult(client: CofheClient, handle: bigint | string): Promise<bigint> {
  return client.decryptForView(handle, FheTypes.Uint32).execute();
}

export function toPriceUnits(price: string): bigint {
  const normalized = price.trim() === '' ? '0' : price.trim();
  return parseUnits(normalized, 18);
}

function requireReceipt(txReceipt: ContractTransactionReceipt | null): ContractTransactionReceipt {
  if (!txReceipt) {
    throw new Error('Transaction receipt missing');
  }
  return txReceipt;
}

function findEventArg(
  contract: Contract,
  receipt: ContractTransactionReceipt,
  eventName: string,
  argName: string,
): bigint {
  for (const log of receipt.logs) {
    try {
      const parsed = contract.interface.parseLog({ topics: log.topics, data: log.data });
      if (parsed && parsed.name === eventName) {
        const value = parsed.args[argName];
        if (typeof value === 'bigint') {
          return value;
        }
      }
    } catch {
      continue;
    }
  }

  throw new Error(`Unable to find ${eventName}.${argName} in transaction logs`);
}

export async function registerMockModel(params: {
  client: CofheClient;
  modelRegistry: Contract;
  pricePerQuery: bigint;
}): Promise<RegisteredModelReceipt> {
  const mockModel = createMockDiabetesModel();
  const encryptedWeights = await encryptUint32Array(params.client, mockModel.weights);
  const encryptedBias = await encryptUint32(params.client, mockModel.bias);

  const tx = await params.modelRegistry.registerModel(
    encryptedWeights,
    encryptedBias,
    params.pricePerQuery,
    mockModel.ipfsHash,
  );
  const receipt = requireReceipt(await tx.wait());
  const modelId = findEventArg(params.modelRegistry, receipt, 'ModelRegistered', 'modelId');

  return { modelId, receipt };
}

export async function submitInference(params: {
  client: CofheClient;
  blindInference: Contract;
  modelId: bigint;
  inputs: number[];
}): Promise<InferenceSubmission> {
  const encryptedInputs = await encryptUint32Array(params.client, params.inputs);
  const inferenceTx = await params.blindInference.predict(params.modelId, encryptedInputs);
  const inferenceReceipt = requireReceipt(await inferenceTx.wait());
  const requestId = findEventArg(params.blindInference, inferenceReceipt, 'PredictionRequested', 'requestId');

  return {
    requestId,
    receipt: inferenceReceipt,
  };
}
