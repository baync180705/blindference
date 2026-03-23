/**
 * Mock FHE Service for BLINFERENCE
 * Simulates Fhenix cofhejs and InferenceEngine.sol behavior
 */

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

export async function encrypt_uint32(value: number): Promise<string> {
  // Mock encryption: returns a hex-like string representing the encrypted value
  await sleep(10); // Simulate some work
  return `0xENC_${value.toString(16).padStart(8, '0')}`;
}

export async function mockEncrypt(data: any, onProgress: (msg: string) => void) {
  onProgress("Initializing local FHE context...");
  await sleep(800);
  onProgress("Generating ephemeral public keys...");
  await sleep(600);
  onProgress("Encrypting biomarkers locally (AES-GCM + TFHE)...");
  await sleep(1000);
  return "0x" + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

export async function mockSubmitToChain(ciphertext: string, onProgress: (msg: string) => void) {
  onProgress("Submitting ciphertext to Fhenix Network...");
  await sleep(1200);
  onProgress("Transaction confirmed: 0x82f...91a");
  await sleep(500);
  onProgress("Running FHE.mul/add on-chain (Blind Inference)...");
  await sleep(2000);
  onProgress("Computation complete. Sealed handle generated.");
  return "0x" + Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

export async function mockDecrypt(handle: string) {
  await sleep(1500);
  const result = Math.random() > 0.5 ? "High Risk Detected" : "Low Risk Detected";
  return result;
}
