import type { Address, Hex, PublicClient, WalletClient } from "viem";
import { decodeEventLog, keccak256, toHex } from "viem";

import { priceOracleAbi, tradingLossUnderwriterAbi, tradingSignalAttestorAbi } from "./abis.js";
import {
  type Bytes32,
  type ClaimResult,
  type ClientConfig,
  type Coverage,
  CoverageMissingError,
  type Direction,
  type PurchaseCoverageParams,
  type Signal,
  SignalNotFoundError,
} from "./types.js";

export interface TradingSignalClientArgs {
  config: ClientConfig;
  publicClient: PublicClient;
  /** Optional — required only for `purchaseCoverage` and `claimLoss`. */
  walletClient?: WalletClient;
}

/**
 * Read + write interface to the insured Trading Signal Agent.
 *
 * Read paths use the `publicClient`. Write paths require a `walletClient`
 * with an account; the client signs and submits transactions.
 */
export class TradingSignalClient {
  private readonly addresses: ClientConfig["addresses"];
  private readonly chainId: number;
  private readonly publicClient: PublicClient;
  private readonly walletClient: WalletClient | undefined;

  constructor({ config, publicClient, walletClient }: TradingSignalClientArgs) {
    this.addresses = config.addresses;
    this.chainId = config.chainId;
    this.publicClient = publicClient;
    this.walletClient = walletClient;
  }

  // ------------------------------------------------------------------
  //  Read paths
  // ------------------------------------------------------------------

  async getSignal(invocationId: bigint): Promise<Signal> {
    const result = (await this.publicClient.readContract({
      address: this.addresses.signalAttestor,
      abi: tradingSignalAttestorAbi,
      functionName: "signalOf",
      args: [invocationId],
    })) as Signal;

    if (result.issuedAt === 0n) {
      throw new SignalNotFoundError(invocationId);
    }
    return result;
  }

  async getCoverage(invocationId: bigint, buyer: Address): Promise<Coverage> {
    const result = (await this.publicClient.readContract({
      address: this.addresses.lossUnderwriter,
      abi: tradingLossUnderwriterAbi,
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
      address: this.addresses.lossUnderwriter,
      abi: tradingLossUnderwriterAbi,
      functionName: "lossThresholdBps",
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

  // ------------------------------------------------------------------
  //  Computations (no chain calls)
  // ------------------------------------------------------------------

  /**
   * Computes the projected loss in basis points if the buyer claimed at the
   * given price. Mirrors `TradingLossUnderwriter._computeLoss` exactly.
   */
  projectedLossBps(signal: Signal, currentPrice: bigint, holdToleranceBps: bigint): bigint {
    if (signal.priceAtIssue <= 0n || currentPrice <= 0n) {
      return 0n;
    }

    const issuePrice = signal.priceAtIssue;

    if (signal.direction === 2 /* BUY */) {
      if (currentPrice >= issuePrice) return 0n;
      const drop = issuePrice - currentPrice;
      return (drop * 10000n) / issuePrice;
    }
    if (signal.direction === 0 /* SELL */) {
      if (currentPrice <= issuePrice) return 0n;
      const rise = currentPrice - issuePrice;
      return (rise * 10000n) / issuePrice;
    }
    // HOLD
    const absMove = currentPrice >= issuePrice ? currentPrice - issuePrice : issuePrice - currentPrice;
    const holdMoveBps = (absMove * 10000n) / issuePrice;
    return holdMoveBps > holdToleranceBps ? holdMoveBps - holdToleranceBps : 0n;
  }

  // ------------------------------------------------------------------
  //  Write paths
  // ------------------------------------------------------------------

  async purchaseCoverage(params: PurchaseCoverageParams): Promise<Hex> {
    const wallet = this._requireWallet("purchaseCoverage");
    const { request } = await this.publicClient.simulateContract({
      address: this.addresses.lossUnderwriter,
      abi: tradingLossUnderwriterAbi,
      functionName: "purchaseCoverage",
      args: [params.invocationId, params.coverageAmount, params.escrowId],
      account: wallet.account!,
      chain: wallet.chain,
    });
    return wallet.writeContract(request);
  }

  async claimLoss(invocationId: bigint): Promise<ClaimResult> {
    const wallet = this._requireWallet("claimLoss");
    const { request } = await this.publicClient.simulateContract({
      address: this.addresses.lossUnderwriter,
      abi: tradingLossUnderwriterAbi,
      functionName: "claimLoss",
      args: [invocationId],
      account: wallet.account!,
      chain: wallet.chain,
    });
    const txHash = await wallet.writeContract(request);

    const receipt = await this.publicClient.waitForTransactionReceipt({ hash: txHash });
    let payoutAmount: bigint | undefined;
    for (const log of receipt.logs) {
      if (log.address.toLowerCase() !== this.addresses.lossUnderwriter.toLowerCase()) continue;
      try {
        const decoded = decodeEventLog({
          abi: tradingLossUnderwriterAbi,
          data: log.data,
          topics: log.topics,
        });
        if (decoded.eventName === "ClaimPaid") {
          payoutAmount = decoded.args.payoutAmount;
          break;
        }
      } catch {
        // not the event we're looking for
      }
    }
    return payoutAmount !== undefined ? { txHash, payoutAmount } : { txHash };
  }

  // ------------------------------------------------------------------
  //  Helpers
  // ------------------------------------------------------------------

  /**
   * Hash an asset symbol to the bytes32 the contracts use as the asset key.
   * Example: `assetKey("ETH/USDC")` → keccak256("ETH/USDC").
   */
  static assetKey(symbol: string): Bytes32 {
    return keccak256(toHex(symbol));
  }

  /**
   * Compute the signal-hash the Blindference quorum signs over.
   * Useful client-side to verify the signal payload matches the on-chain
   * `ExecutionCommitmentRegistry.executorOutput` for the invocation.
   */
  async signalDigest(args: {
    asset: Bytes32;
    direction: Direction;
    confidenceBps: number;
    priceAtIssue: bigint;
    validUntil: bigint;
    agent: Address;
  }): Promise<Bytes32> {
    return this.publicClient.readContract({
      address: this.addresses.signalAttestor,
      abi: tradingSignalAttestorAbi,
      functionName: "signalDigest",
      args: [
        args.asset,
        args.direction,
        args.confidenceBps,
        args.priceAtIssue,
        args.validUntil,
        args.agent,
      ],
    }) as Promise<Bytes32>;
  }

  private _requireWallet(op: string): WalletClient {
    if (!this.walletClient) {
      throw new Error(
        `TradingSignalClient.${op} requires a walletClient — pass one in the constructor`,
      );
    }
    if (!this.walletClient.account) {
      throw new Error(
        `TradingSignalClient.${op}: walletClient is missing an account`,
      );
    }
    return this.walletClient;
  }
}
