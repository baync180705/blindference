import { describe, expect, it, vi } from "vitest";
import type { Address, Hex, PublicClient, WalletClient } from "viem";

import {
  BlindferenceDemoClient,
  CoverageMissingError,
  type ClientConfig,
  type Coverage,
  type InferenceOutput,
  OutputNotFoundError,
  Recommendation,
  recommendationLabel,
} from "../src/index.js";

const ADDRESSES = {
  attestor: "0x1111111111111111111111111111111111111111" as Address,
  underwriter: "0x2222222222222222222222222222222222222222" as Address,
  priceOracle: "0x3333333333333333333333333333333333333333" as Address,
};

const CONFIG: ClientConfig = { addresses: ADDRESSES, chainId: 31337 };
const TRADER: Address = "0xaaaaAAaaAaAAAAaAaAAaaAaaAaaAaAAAAAAaaAa1";
const AGENT: Address = "0xbbbbBBbbBbBBBBbBbBBBbBbbBbbBBBbBBBBbbbB2";
const MODEL_KEY = BlindferenceDemoClient.assetKey("groq:llama3-70b");
const RESPONSE_HASH = BlindferenceDemoClient.assetKey("BUY ETH/USDC WITH 85% CONFIDENCE");

const ASSET = BlindferenceDemoClient.assetKey("ETH/USDC");
const PRICE_AT_ISSUE = 2_500n * 10n ** 8n;

function buildOutput(overrides: Partial<InferenceOutput> = {}): InferenceOutput {
  return {
    invocationId: 1n,
    asset: ASSET,
    recommendation: Recommendation.BUY,
    confidenceBps: 8500,
    priceAtIssue: PRICE_AT_ISSUE,
    issuedAt: 1_700_000_000n,
    validUntil: 1_700_021_600n,
    agent: AGENT,
    responseHash: RESPONSE_HASH,
    modelKey: MODEL_KEY,
    ...overrides,
  };
}

function buildCoverage(overrides: Partial<Coverage> = {}): Coverage {
  return {
    buyer: TRADER,
    coverageAmount: 1_000n * 10n ** 6n,
    escrowId: 9001n,
    purchasedAt: 1_700_000_500n,
    claimed: false,
    ...overrides,
  };
}

function makePublicClient(overrides: Partial<PublicClient> = {}): PublicClient {
  return {
    readContract: vi.fn(),
    simulateContract: vi.fn(),
    waitForTransactionReceipt: vi.fn(),
    ...overrides,
  } as unknown as PublicClient;
}

function makeWalletClient(): WalletClient {
  return {
    account: { address: TRADER, type: "json-rpc" },
    chain: { id: 31337, name: "anvil", nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 } },
    writeContract: vi.fn().mockResolvedValue("0xdeadbeef" as Hex),
  } as unknown as WalletClient;
}

describe("Recommendation enum", () => {
  it("provides round-trip labels for all values", () => {
    expect(recommendationLabel(Recommendation.SELL)).toBe("SELL");
    expect(recommendationLabel(Recommendation.HOLD)).toBe("HOLD");
    expect(recommendationLabel(Recommendation.BUY)).toBe("BUY");
  });
});

describe("BlindferenceDemoClient.assetKey", () => {
  it("hashes a symbol to a 32-byte hex", () => {
    const key = BlindferenceDemoClient.assetKey("ETH/USDC");
    expect(key).toMatch(/^0x[0-9a-f]{64}$/);
    expect(BlindferenceDemoClient.assetKey("ETH/USDC")).toBe(key);
    expect(BlindferenceDemoClient.assetKey("BTC/USDC")).not.toBe(key);
  });
});

describe("BlindferenceDemoClient.getInferenceOutput", () => {
  it("returns output when present", async () => {
    const expected = buildOutput();
    const publicClient = makePublicClient({
      readContract: vi.fn().mockResolvedValue(expected),
    });
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient });

    const result = await client.getInferenceOutput(1n);
    expect(result).toEqual(expected);
  });

  it("throws OutputNotFoundError when issuedAt is zero", async () => {
    const publicClient = makePublicClient({
      readContract: vi.fn().mockResolvedValue(buildOutput({ issuedAt: 0n })),
    });
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient });

    await expect(client.getInferenceOutput(1n)).rejects.toBeInstanceOf(OutputNotFoundError);
  });
});

describe("BlindferenceDemoClient.getCoverage", () => {
  it("returns coverage when present", async () => {
    const expected = buildCoverage();
    const publicClient = makePublicClient({
      readContract: vi.fn().mockResolvedValue(expected),
    });
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient });

    const result = await client.getCoverage(1n, TRADER);
    expect(result).toEqual(expected);
  });

  it("throws CoverageMissingError when purchasedAt is zero", async () => {
    const publicClient = makePublicClient({
      readContract: vi.fn().mockResolvedValue(buildCoverage({ purchasedAt: 0n })),
    });
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient });

    await expect(client.getCoverage(1n, TRADER)).rejects.toBeInstanceOf(CoverageMissingError);
  });
});

describe("BlindferenceDemoClient.projectedLossBps", () => {
  const HOLD_TOLERANCE = 100n;

  it("returns 0 for a profitable BUY", () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    const output = buildOutput({ recommendation: Recommendation.BUY });
    const lossBps = client.projectedLossBps(output, (PRICE_AT_ISSUE * 110n) / 100n, HOLD_TOLERANCE);
    expect(lossBps).toBe(0n);
  });

  it("returns 5% loss for a BUY where price dropped 5%", () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    const output = buildOutput({ recommendation: Recommendation.BUY });
    const lossBps = client.projectedLossBps(output, (PRICE_AT_ISSUE * 95n) / 100n, HOLD_TOLERANCE);
    expect(lossBps).toBe(500n);
  });

  it("returns 10% loss for a SELL where price rose 10%", () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    const output = buildOutput({ recommendation: Recommendation.SELL });
    const lossBps = client.projectedLossBps(output, (PRICE_AT_ISSUE * 110n) / 100n, HOLD_TOLERANCE);
    expect(lossBps).toBe(1000n);
  });

  it("returns 0 for a SELL where price dropped", () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    const output = buildOutput({ recommendation: Recommendation.SELL });
    const lossBps = client.projectedLossBps(output, (PRICE_AT_ISSUE * 90n) / 100n, HOLD_TOLERANCE);
    expect(lossBps).toBe(0n);
  });

  it("returns 0 for HOLD within tolerance", () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    const output = buildOutput({ recommendation: Recommendation.HOLD });
    const lossBps = client.projectedLossBps(output, (PRICE_AT_ISSUE * 1005n) / 1000n, HOLD_TOLERANCE);
    expect(lossBps).toBe(0n);
  });

  it("returns only the excess move for HOLD", () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    const output = buildOutput({ recommendation: Recommendation.HOLD });
    const lossBps = client.projectedLossBps(output, (PRICE_AT_ISSUE * 105n) / 100n, HOLD_TOLERANCE);
    expect(lossBps).toBe(400n);
  });
});

describe("BlindferenceDemoClient.purchaseCoverage", () => {
  it("requires a wallet client", async () => {
    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient: makePublicClient() });
    await expect(
      client.purchaseCoverage({ invocationId: 1n, coverageAmount: 100n, escrowId: 9001n }),
    ).rejects.toThrow(/wallet/i);
  });

  it("simulates then writes when wallet present", async () => {
    const writeContract = vi.fn().mockResolvedValue("0xfeed" as Hex);
    const publicClient = makePublicClient({
      simulateContract: vi.fn().mockResolvedValue({ request: { __sim: true } }),
    });
    const walletClient = { ...makeWalletClient(), writeContract } as unknown as WalletClient;

    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient, walletClient });
    const txHash = await client.purchaseCoverage({
      invocationId: 1n,
      coverageAmount: 1_000_000n,
      escrowId: 9001n,
    });

    expect(publicClient.simulateContract).toHaveBeenCalledOnce();
    expect(writeContract).toHaveBeenCalledOnce();
    expect(txHash).toBe("0xfeed");
  });
});

describe("BlindferenceDemoClient.claimLoss", () => {
  it("returns tx hash even when payout decode is skipped", async () => {
    const writeContract = vi.fn().mockResolvedValue("0xabcd" as Hex);
    const publicClient = makePublicClient({
      simulateContract: vi.fn().mockResolvedValue({ request: {} }),
      waitForTransactionReceipt: vi.fn().mockResolvedValue({
        logs: [
          {
            address: ADDRESSES.underwriter,
            topics: [],
            data: "0x",
          },
        ],
      }),
    });
    const walletClient = { ...makeWalletClient(), writeContract } as unknown as WalletClient;

    const client = new BlindferenceDemoClient({ config: CONFIG, publicClient, walletClient });
    const result = await client.claimLoss(1n);

    expect(result.txHash).toBe("0xabcd");
  });
});
