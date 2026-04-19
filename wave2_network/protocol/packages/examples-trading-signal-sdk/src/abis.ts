// Hand-written minimal ABIs — only the functions the SDK uses.
// For the full ABIs run `forge inspect <contract> abi` against the contracts package.

export const tradingSignalAttestorAbi = [
  {
    type: "function",
    name: "signalOf",
    stateMutability: "view",
    inputs: [{ name: "invocationId", type: "uint256" }],
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [
          { name: "invocationId", type: "uint256" },
          { name: "asset", type: "bytes32" },
          { name: "direction", type: "uint8" },
          { name: "confidenceBps", type: "uint16" },
          { name: "priceAtIssue", type: "int256" },
          { name: "issuedAt", type: "uint64" },
          { name: "validUntil", type: "uint64" },
          { name: "agent", type: "address" },
        ],
      },
    ],
  },
  {
    type: "function",
    name: "signalDigest",
    stateMutability: "pure",
    inputs: [
      { name: "asset", type: "bytes32" },
      { name: "direction", type: "uint8" },
      { name: "confidenceBps", type: "uint16" },
      { name: "priceAtIssue", type: "int256" },
      { name: "validUntil", type: "uint64" },
      { name: "agent", type: "address" },
    ],
    outputs: [{ name: "", type: "bytes32" }],
  },
  {
    type: "event",
    name: "SignalCommitted",
    inputs: [
      { name: "invocationId", type: "uint256", indexed: true },
      { name: "asset", type: "bytes32", indexed: true },
      { name: "direction", type: "uint8", indexed: true },
      { name: "confidenceBps", type: "uint16", indexed: false },
      { name: "priceAtIssue", type: "int256", indexed: false },
      { name: "validUntil", type: "uint64", indexed: false },
      { name: "agent", type: "address", indexed: false },
    ],
    anonymous: false,
  },
] as const;

export const tradingLossUnderwriterAbi = [
  {
    type: "function",
    name: "purchaseCoverage",
    stateMutability: "nonpayable",
    inputs: [
      { name: "invocationId", type: "uint256" },
      { name: "coverageAmount", type: "uint256" },
      { name: "escrowId", type: "uint256" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "claimLoss",
    stateMutability: "nonpayable",
    inputs: [{ name: "invocationId", type: "uint256" }],
    outputs: [],
  },
  {
    type: "function",
    name: "coverageOf",
    stateMutability: "view",
    inputs: [
      { name: "invocationId", type: "uint256" },
      { name: "buyer", type: "address" },
    ],
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [
          { name: "buyer", type: "address" },
          { name: "coverageAmount", type: "uint256" },
          { name: "escrowId", type: "uint256" },
          { name: "purchasedAt", type: "uint64" },
          { name: "claimed", type: "bool" },
        ],
      },
    ],
  },
  {
    type: "function",
    name: "lossThresholdBps",
    stateMutability: "view",
    inputs: [],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    type: "event",
    name: "CoveragePurchased",
    inputs: [
      { name: "invocationId", type: "uint256", indexed: true },
      { name: "buyer", type: "address", indexed: true },
      { name: "coverageAmount", type: "uint256", indexed: false },
      { name: "escrowId", type: "uint256", indexed: false },
    ],
    anonymous: false,
  },
  {
    type: "event",
    name: "ClaimPaid",
    inputs: [
      { name: "invocationId", type: "uint256", indexed: true },
      { name: "buyer", type: "address", indexed: true },
      { name: "payoutAmount", type: "uint256", indexed: false },
      { name: "priceAtIssue", type: "int256", indexed: false },
      { name: "priceAtClaim", type: "int256", indexed: false },
    ],
    anonymous: false,
  },
] as const;

export const priceOracleAbi = [
  {
    type: "function",
    name: "latestAnswer",
    stateMutability: "view",
    inputs: [{ name: "asset", type: "bytes32" }],
    outputs: [
      { name: "price", type: "int256" },
      { name: "updatedAt", type: "uint256" },
    ],
  },
] as const;
