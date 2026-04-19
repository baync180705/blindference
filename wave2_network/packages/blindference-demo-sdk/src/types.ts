import type { Address, Hex } from "viem";

export type Bytes32 = Hex;

export const Recommendation = {
  SELL: 0,
  HOLD: 1,
  BUY: 2,
} as const;
export type Recommendation = (typeof Recommendation)[keyof typeof Recommendation];

export function recommendationLabel(value: Recommendation): "SELL" | "HOLD" | "BUY" {
  switch (value) {
    case Recommendation.SELL:
      return "SELL";
    case Recommendation.HOLD:
      return "HOLD";
    case Recommendation.BUY:
      return "BUY";
  }
}

export interface InferenceOutput {
  invocationId: bigint;
  asset: Bytes32;
  recommendation: Recommendation;
  confidenceBps: number;
  priceAtIssue: bigint;
  issuedAt: bigint;
  validUntil: bigint;
  agent: Address;
  responseHash: Bytes32;
  modelKey: Bytes32;
}

export interface Coverage {
  buyer: Address;
  coverageAmount: bigint;
  escrowId: bigint;
  purchasedAt: bigint;
  claimed: boolean;
}

export interface ContractAddresses {
  attestor: Address;
  underwriter: Address;
  priceOracle: Address;
}

export interface ClientConfig {
  addresses: ContractAddresses;
  chainId: number;
}

export interface PurchaseCoverageParams {
  invocationId: bigint;
  coverageAmount: bigint;
  escrowId: bigint;
}

export interface ClaimResult {
  txHash: Hex;
  payoutAmount?: bigint;
}

export class OutputNotFoundError extends Error {
  constructor(invocationId: bigint) {
    super(`Inference output not found for invocation ${invocationId.toString()}`);
    this.name = "OutputNotFoundError";
  }
}

export class CoverageMissingError extends Error {
  constructor(invocationId: bigint, buyer: Address) {
    super(`No coverage purchased by ${buyer} for invocation ${invocationId.toString()}`);
    this.name = "CoverageMissingError";
  }
}
