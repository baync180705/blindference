import type { Address, Hex, PublicClient, WalletClient } from "viem";
import { decodeEventLog, keccak256, toHex } from "viem";

import { blindferenceAttestorAbi, blindferenceUnderwriterAbi, priceOracleAbi } from "./abis.js";
import {
  type Bytes32,
  type ClaimResult,
  type ClientConfig,
  type Coverage,
  CoverageMissingError,
  type InferenceOutput,
  OutputNotFoundError,
  type PurchaseCoverageParams,
  type Recommendation,
} from "./types.js";

export interface BlindferenceDemoClientArgs {
  config: ClientConfig;
  publicClient: PublicClient;
  walletClient?: WalletClient;
}

export class BlindferenceDemoClient {
  private readonly addresses: ClientConfig["addresses"];
  private readonly chainId: number;
  private readonly publicClient: PublicClient;
  private readonly walletClient: WalletClient | undefined;

  constructor({ config, publicClient, walletClient }: BlindferenceDemoClientArgs) {
    this.addresses = config.addresses;
    this.chainId = config.chainId;
    this.publicClient = publicClient;
    this.walletClient = walletClient;
  }

  async getInferenceOutput(invocationId: bigint): Promise<InferenceOutput> {
    const result = (await this.publicClient.readContract({
      address: this.addresses.attestor,
      abi: blindferenceAttestorAbi,
      functionName: "outputOf",
      args: [invocationId],
    })) as InferenceOutput;

    if (result.issuedAt === 0n) {
      throw new OutputNotFoundError(invocationId);
    }
    return result;
  }

  async getCoverage(invocationId: bigint, buyer: Address): Promise<Coverage> {
    const result = (await this.publicClient.readContract({
      address: this.addresses.underwriter,
      abi: blindferenceUnderwriterAbi,
      functionName: "coverageOf",
      args: [invocationId, buyer],
    })) as Coverage;

    if (result.purchasedAt === 0n) {
      throw new CoverageMissingError(invocationId, buyer);
    }
    return result;
  }

  async getLossThresholdBps(): Promise<bigint> {
    return this.publicClient.readContract({
      address: this.addresses.underwriter,
      abi: blindferenceUnderwriterAbi,
      functionName: "lossThresholdBps",
    }) as Promise<bigint>;
  }

  async getHoldToleranceBps(): Promise<bigint> {
    return this.publicClient.readContract({
      address: this.addresses.underwriter,
      abi: blindferenceUnderwriterAbi,
      functionName: "holdToleranceBps",
    }) as Promise<bigint>;
  }

  async getCurrentPrice(asset: Bytes32): Promise<{ price: bigint; updatedAt: bigint }> {
    const [price, updatedAt] = (await this.publicClient.readContract({
      address: this.addresses.priceOracle,
      abi: priceOracleAbi,
      functionName: "latestAnswer",
      args: [asset],
    })) as readonly [bigint, bigint];
    return { price, updatedAt };
  }

  projectedLossBps(output: InferenceOutput, currentPrice: bigint, holdToleranceBps: bigint): bigint {
    if (output.priceAtIssue <= 0n || currentPrice <= 0n) {
      return 0n;
    }

    const issuePrice = output.priceAtIssue;

    if (output.recommendation === 2) {
      if (currentPrice >= issuePrice) return 0n;
      const drop = issuePrice - currentPrice;
      return (drop * 10_000n) / issuePrice;
    }

    if (output.recommendation === 0) {
      if (currentPrice <= issuePrice) return 0n;
      const rise = currentPrice - issuePrice;
      return (rise * 10_000n) / issuePrice;
    }

    const absMove = currentPrice >= issuePrice ? currentPrice - issuePrice : issuePrice - currentPrice;
    const holdMoveBps = (absMove * 10_000n) / issuePrice;
    return holdMoveBps > holdToleranceBps ? holdMoveBps - holdToleranceBps : 0n;
  }

  async purchaseCoverage(params: PurchaseCoverageParams): Promise<Hex> {
    const wallet = this.requireWallet("purchaseCoverage");
    const { request } = await this.publicClient.simulateContract({
      address: this.addresses.underwriter,
      abi: blindferenceUnderwriterAbi,
      functionName: "purchaseCoverage",
      args: [params.invocationId, params.coverageAmount, params.escrowId],
      account: wallet.account!,
      chain: wallet.chain,
    });
    return wallet.writeContract(request);
  }

  async claimLoss(invocationId: bigint): Promise<ClaimResult> {
    const wallet = this.requireWallet("claimLoss");
    const { request } = await this.publicClient.simulateContract({
      address: this.addresses.underwriter,
      abi: blindferenceUnderwriterAbi,
      functionName: "claimLoss",
      args: [invocationId],
      account: wallet.account!,
      chain: wallet.chain,
    });
    const txHash = await wallet.writeContract(request);

    const receipt = await this.publicClient.waitForTransactionReceipt({ hash: txHash });
    let payoutAmount: bigint | undefined;
    for (const log of receipt.logs) {
      if (log.address.toLowerCase() !== this.addresses.underwriter.toLowerCase()) continue;
      try {
        const decoded = decodeEventLog({
          abi: blindferenceUnderwriterAbi,
          data: log.data,
          topics: log.topics,
        });
        if (decoded.eventName === "ClaimPaid") {
          payoutAmount = decoded.args.payoutAmount;
          break;
        }
      } catch {
        continue;
      }
    }

    return payoutAmount !== undefined ? { txHash, payoutAmount } : { txHash };
  }

  static assetKey(symbol: string): Bytes32 {
    return keccak256(toHex(symbol));
  }

  async outputDigest(args: {
    responseHash: Bytes32;
    asset: Bytes32;
    recommendation: Recommendation;
    confidenceBps: number;
    priceAtIssue: bigint;
    validUntil: bigint;
    agent: Address;
    modelKey: Bytes32;
  }): Promise<Bytes32> {
    return this.publicClient.readContract({
      address: this.addresses.attestor,
      abi: blindferenceAttestorAbi,
      functionName: "outputDigest",
      args: [
        args.responseHash,
        args.asset,
        args.recommendation,
        args.confidenceBps,
        args.priceAtIssue,
        args.validUntil,
        args.agent,
        args.modelKey,
      ],
    }) as Promise<Bytes32>;
  }

  private requireWallet(op: string): WalletClient {
    if (!this.walletClient) {
      throw new Error(`BlindferenceDemoClient.${op} requires a walletClient`);
    }
    if (!this.walletClient.account) {
      throw new Error(`BlindferenceDemoClient.${op} requires a wallet account`);
    }
    return this.walletClient;
  }
}
