# Architecture

## Overview

Blindference Wave 2 is a confidential risk-scoring pipeline with economic settlement:

1. The frontend encrypts loan features with CoFHE in the user's wallet.
2. The ICL previews and assigns a quorum of `1 leader + 2 verifiers`.
3. The frontend creates one CoFHE sharing permit per quorum node and submits the encrypted payload plus permits.
4. Each node decrypts locally, runs inference through Groq or Gemini, and submits a signed result or verifier verdict.
5. The ICL aggregates the quorum, commits the final result hash to `ExecutionCommitmentRegistry`, and records demo settlement metadata.
6. The frontend renders the full journey: assignment, execution, verification, commitment, coverage, and mock escrow release.

## Main Components

### Frontend

Location: `wave2_network/packages/frontend`

- BF demo UI transplanted into the active monorepo
- Wallet connection via `wagmi`
- Real CoFHE browser client via `@cofhe/sdk`
- Multi-recipient permit creation for leader and verifiers
- Status polling and visual quorum progress

### ICL

Location: `wave2_network/packages/icl`

- FastAPI coordination layer
- Quorum preview and task assignment
- Permit-aware request intake
- Leader result and verifier verdict ingestion
- Final quorum aggregation and on-chain execution finalization
- Demo metadata for coverage and visible escrow release evidence

### Node Runtime

Location: `wave2_network/packages/node-reineira`

- One process per operator key
- Role detection: leader or verifier
- CoFHE decrypt path with shared permits
- Hosted inference via Groq or Gemini
- Result hashing and submission back to ICL

### Contracts

Locations:

- `wave2_network/packages/contracts`
- `wave2_network/packages/blindference-demo`

Core protocol:

- `NodeAttestationRegistry`
- `ExecutionCommitmentRegistry`
- `AgentConfigRegistry`
- `ReputationRegistry`
- `RewardAccumulator`

Demo vertical:

- `BlindferenceAgent`
- `BlindferenceAttestor`
- `BlindferenceUnderwriter`
- `MockPriceOracle`

## Privacy Model

- The ICL never receives plaintext loan features.
- Ciphertexts are created in the browser.
- The user shares CoFHE permits only with the selected quorum members.
- Each node decrypts locally with its own wallet-scoped permit.
- Verifiers work from the same encrypted payload, not a plaintext copy from the coordinator.

## Demo Settlement Model

The buildathon demo uses:

- real on-chain execution commitment on Arbitrum Sepolia
- real quorum selection and result aggregation
- real coverage and dispute surfaces in the UI
- a mock escrow release evidence step after accepted scoring so the demo shows the full economic lifecycle without requiring a production escrow release backend

## Package Boundaries

```text
wave2_network/
├── packages/contracts/         Core protocol
├── packages/blindference-demo/ Demo contracts
├── packages/icl/               Coordination backend
├── packages/frontend/          User-facing BF app
├── packages/node-reineira/     Quorum node runtime
├── packages/fhe-mocks/         Optional local FHE mocks
└── protocol/                   Reineira upstream reference
```

## Remaining Non-Final Pieces

- Production identity / ERC-8004 registry replacement for mocks
- Production escrow release path instead of demo settlement metadata
- Production oracle / policy hardening for disputes and underwriting
- Full operator lifecycle automation for reputation, rewards, and staking
