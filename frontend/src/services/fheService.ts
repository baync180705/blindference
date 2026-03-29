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


export const sleep = (ms: number) => new globalThis.Promise(resolve => setTimeout(resolve, ms));

export async function encrypt_uint32(value: number): Promise<string> {
  // Mock encryption: returns a hex-like string representing the encrypted value
  await sleep(10); // Simulate some work
  return `0xENC_${value.toString(16).padStart(8, '0')}`;
}

export const mockEncrypt = async (
  data: Record<string, string>,
  logFn: (msg: string) => void
): Promise<string> => {
  logFn("Serializing biomarker data...");
  await sleep(500);
  logFn("Applying FHE encryption to parameters...");
  await sleep(1000);
  const cipher = "0x" + Array.from({length: 64}, () => Math.floor(Math.random()*16).toString(16)).join('');
  logFn(`Ciphertext generated: ${cipher.substring(0, 16)}...`);
  return cipher;
};

export const mockSubmitToChain = async (
  cipher: string,
  logFn: (msg: string) => void
): Promise<string> => {
  logFn("Submitting encrypted payload to AI Lab Smart Contract...");
  await sleep(800);
  logFn("Awaiting transaction confirmation block...");
  await sleep(1500);
  logFn("Inference request logged on Fhenix L2.");
  return "0xSEALED_" + Math.random().toString(36).substring(2, 10).toUpperCase();
};

export const mockDecrypt = async (handle: string): Promise<string> => {
  await sleep(1500);
  const results = ["High Risk: Type 2 Diabetes", "Normal Range", "Elevated Risk: Pre-diabetes"];
  return results[Math.floor(Math.random() * results.length)];
};

