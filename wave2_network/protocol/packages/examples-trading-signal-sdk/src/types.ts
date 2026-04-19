import type { Address, Hex } from "viem";

export type Bytes32 = Hex;

/// Wire-compatible with on-chain `ITradingSignalAttestor.Direction`.
export const Direction = {
  SELL: 0,
  HOLD: 1,
  BUY: 2,
} as const;
export type Direction = (typeof Direction)[keyof typeof Direction];

export function directionLabel(d: Direction): "SELL" | "HOLD" | "BUY" {
  switch (d) {
    case Direction.SELL:
      return "SELL";
    case Direction.HOLD:
      return "HOLD";
    case Direction.BUY:
      return "BUY";
  }
}

export interface Signal {
  invocationId: bigint;
  asset: Bytes32;
  direction: Direction;
  confidenceBps: number;
  priceAtIssue: bigint;
  issuedAt: bigint;
  validUntil: bigint;
  agent: Address;
}

export interface Coverage {
  buyer: Address;
  coverageAmount: bigint;
  escrowId: bigint;
  purchasedAt: bigint;
  claimed: boolean;
}

export interface ContractAddresses {
  signalAttestor: Address;
  lossUnderwriter: Address;
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

export class SignalNotFoundError extends Error {
  constructor(invocationId: bigint) {
    super(`Signal not found for invocation ${invocationId.toString()}`);
    this.name = "SignalNotFoundError";
  }
}

export class CoverageMissingError extends Error {
  constructor(invocationId: bigint, buyer: Address) {
    super(`No coverage purchased by ${buyer} for invocation ${invocationId.toString()}`);
    this.name = "CoverageMissingError";
  }
}
