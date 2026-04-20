# Blindference Wave 2

Blindference Wave 2 is a privacy-preserving SLA and settlement layer for Web3 AI. It coordinates encrypted inference across a quorum of independent nodes, verifies the outcome economically, and records the accepted result on Arbitrum Sepolia.

The current demo focuses on confidential credit-risk scoring. A user encrypts loan features with CoFHE, Blindference selects a `1 leader + 2 verifier` quorum, each node decrypts locally under user-scoped permits, inference runs off-chain through Groq or Gemini, and the accepted result is committed on-chain with visible coverage and settlement evidence.

Blindference is built in collaboration with:

- Reineira: https://reineira.xyz/
- Fhenix / CoFHE: https://www.fhenix.io/

## Executive Summary

Wave 2 is the productized version of Blindference. Instead of treating privacy as a single-contract or single-model problem, Wave 2 treats AI execution as a full lifecycle:

- private input submission
- quorum-based execution
- verifier-backed acceptance
- on-chain commitment
- coverage and dispute surfaces
- settlement visibility

This makes Blindference a stronger fit for Web3 AI: users care not only that their inputs are private, but also that the result is accountable, challengeable, and economically meaningful.

## Why We Shifted From Wave 1

Blindference Wave 1 explored confidential inference primitives. That was valuable research, but it did not yet express the strongest product story for a buildathon or a practical deployment path.

Wave 2 is a deliberate shift:

- from isolated confidential inference to a complete execution SLA layer
- from only privacy to privacy plus verification plus settlement
- from a single inference actor to a leader-and-verifier quorum
- from model-centric experimentation to a developer-facing execution pipeline
- from local-model assumptions to hosted frontier-model execution, because physical GPU constraints made coordination and accountability more valuable than forcing on-device inference

The result is a clearer product thesis:

- the user keeps sensitive data private
- the coordinator never needs plaintext
- multiple nodes independently execute and verify
- the accepted output is committed on-chain
- the economic path around the result is visible

## What Blindference Offers

- Browser-side encrypted input handling using CoFHE
- Selective disclosure through per-node sharing permits
- Quorum-based execution using `1 leader + 2 verifiers`
- Hosted inference with frontier models such as:
  - `groq:llama-3.3-70b-versatile`
  - `gemini:gemini-2.5-flash`
- On-chain result commitment on Arbitrum Sepolia
- Coverage, dispute, and settlement surfaces for a recordable demo lifecycle
- A polished frontend wired to the real backend and contract flow

## Core Demo Scenario

In the current buildathon vertical, Blindference demonstrates confidential loan-risk scoring:

1. The user enters loan features in the frontend.
2. The frontend encrypts those features with CoFHE.
3. The frontend asks the ICL for a quorum preview.
4. The frontend creates one sharing permit for each selected node.
5. The ICL creates the task and routes encrypted input plus node-specific permits.
6. The leader and verifiers decrypt locally and run the same scoring task.
7. The ICL aggregates the quorum and commits the accepted result on-chain.
8. The frontend shows the full journey, including coverage and demo settlement evidence.

## Architecture

Blindference Wave 2 has five main layers.

### 1. Frontend

The frontend is the user entry point. It handles:

- wallet connection
- feature entry
- CoFHE encryption
- quorum preview
- sharing permit creation
- request submission
- live status polling
- dispute and settlement visibility

### 2. ICL

The Inference Coordination Layer is the control plane. It handles:

- request intake
- quorum selection
- encrypted task routing
- node-specific permit handling
- leader result ingestion
- verifier verdict ingestion
- quorum aggregation
- on-chain finalization

### 3. Node Runtime

Each node runtime is tied to an operator key and can act as leader or verifier. It handles:

- permit-based local decryption
- model execution through Groq or Gemini
- result hashing
- signed result or verdict submission back to the ICL

### 4. Protocol Contracts

Core protocol contracts on Arbitrum Sepolia provide registry and commitment infrastructure:

- `NodeAttestationRegistry`
- `ExecutionCommitmentRegistry`
- `AgentConfigRegistry`
- `ReputationRegistry`
- `RewardAccumulator`

### 5. Demo Settlement Layer

The Blindference demo contracts provide the visible buildathon settlement flow:

- `BlindferenceAgent`
- `BlindferenceAttestor`
- `BlindferenceUnderwriter`
- `MockPriceOracle`

### Architecture Summary

```text
User Wallet + Frontend
  -> encrypt features with CoFHE
  -> preview quorum
  -> create one permit per quorum member
  -> submit encrypted request

ICL
  -> assign leader + verifiers
  -> route encrypted payloads and permits
  -> ingest leader result and verifier verdicts
  -> aggregate quorum
  -> finalize on-chain commitment

Node Quorum
  -> decrypt locally with permit
  -> run Groq / Gemini inference
  -> sign and submit outputs

Arbitrum Sepolia
  -> registry state
  -> execution commitment
  -> demo coverage and settlement evidence
```

## Privacy Model

Blindference Wave 2 is designed so the coordinator is not the holder of sensitive input data.

- The frontend encrypts; the coordinator does not.
- The ICL does not need plaintext features to do its job.
- The user grants access only to the selected quorum members.
- Each node decrypts locally using its own wallet-scoped permit.
- Verifiers work from the same encrypted payload, not from a plaintext relay.

## Monorepo Structure

The active codebase lives under [`wave2_network`](./wave2_network).

```text
blindference/
├── ARCHITECTURE.md
├── DEPLOYMENT.md
├── README.md
└── wave2_network/
    ├── packages/contracts/           Reineira-aligned protocol contracts
    ├── packages/blindference-demo/   Blindference demo contracts
    ├── packages/icl/                 FastAPI inference coordination layer
    ├── packages/frontend/            Active Blindference frontend
    ├── packages/node-reineira/       Leader / verifier node runtime
    ├── packages/fhe-mocks/           Optional local FHE helpers
    └── protocol/                     Upstream Reineira reference code
```

## Package Guide

- `wave2_network/packages/contracts`
  - Reineira-aligned protocol contracts and Foundry tests
- `wave2_network/packages/blindference-demo`
  - Blindference demo contracts for coverage and settlement flow
- `wave2_network/packages/icl`
  - FastAPI coordination backend
- `wave2_network/packages/frontend`
  - user-facing Blindference app
- `wave2_network/packages/node-reineira`
  - leader and verifier node processes
- `wave2_network/protocol`
  - upstream reference implementation retained for alignment and context

## Technology Stack

- Smart contracts: Solidity, Foundry
- Coordination backend: FastAPI, Pydantic, Web3.py
- Frontend: React, Vite, Tailwind, wagmi, viem, `@cofhe/sdk`
- Node runtime: Python with a Node bridge for CoFHE integration
- Inference providers: Groq and Google Gemini
- Network layer:
  - Arbitrum Sepolia for commitments and registry state
  - CoFHE testnet RPC for encrypted input and permit flows

## Supported Model IDs

The current runtime is aligned around these hosted model identifiers:

- `groq:llama-3.3-70b-versatile`
- `gemini:gemini-2.5-flash`

These IDs must stay aligned across:

- the frontend
- the ICL model catalog
- the node runtime configuration

## Prerequisites

- Node.js 20+
- npm 10+
- Python 3.11+
- Foundry
- MetaMask or another EVM wallet
- Arbitrum Sepolia ETH for:
  - the ICL wallet
  - operator wallets
  - the user wallet

Helpful extras:

- MongoDB for persistent local state
- `jq`
- `curl`

## Environment Matrix

For reproducibility, keep the stack aligned like this:

| Component | Primary Endpoint / Network | Responsibility |
| --- | --- | --- |
| Frontend | Arbitrum Sepolia + CoFHE RPC | wallet flow, encryption, permit creation |
| ICL | Arbitrum Sepolia RPC | coordination and on-chain finalization |
| Node Runtime | CoFHE RPC + Groq or Gemini API | local decrypt + off-chain inference |
| Contracts | Arbitrum Sepolia | registries, commitments, coverage demo state |

## Environment Configuration

Only `.env.example` files should be committed. Copy them locally before running the stack.

### ICL

File: [`wave2_network/packages/icl/.env.example`](./wave2_network/packages/icl/.env.example)

```env
MONGO_URI=mongodb://localhost:27017
ARBITRUM_SEPOLIA_RPC=https://sepolia-rollup.arbitrum.io/rpc
NODE_ATTESTATION_REGISTRY_ADDRESS=0x...
EXECUTION_COMMITMENT_REGISTRY_ADDRESS=0x...
AGENT_CONFIG_REGISTRY_ADDRESS=0x...
REPUTATION_REGISTRY_ADDRESS=0x...
REWARD_ACCUMULATOR_ADDRESS=0x...
ICL_PRIVATE_KEY=
COFHE_RPC_URL=https://testnet-cofhe.fhenix.zone
COFHE_CHAIN_ID=421614
DEFAULT_VERIFIER_COUNT=2
BLINDFERENCE_ATTESTOR_ADDRESS=0x74454F689F28EfbEF6Ef9F3F14e56ac62CA8EC49
BLINDFERENCE_UNDERWRITER_ADDRESS=0xcbbdcb1b42DE4Ed52f7ceD752c65652EE317B601
BLINDFERENCE_AGENT_ADDRESS=0xc9208B8aCAaD3abFc955a575719BB8F21640A6fE
MOCK_ORACLE_ADDRESS=0xDe9AE4b048bF320Db6492e2AfD0516392EBA05Fc
DEMO_OPERATOR_PRIVATE_KEYS=
MOCK_CHAIN=false
```

### Node Runtime

File: [`wave2_network/packages/node-reineira/.env.example`](./wave2_network/packages/node-reineira/.env.example)

```env
BLINDFERENCE_NODE_ICL_BASE_URL=http://localhost:8000
BLINDFERENCE_NODE_PROVIDER=groq
BLINDFERENCE_NODE_GROQ_MODEL=llama-3.3-70b-versatile
BLINDFERENCE_NODE_GEMINI_MODEL=gemini-2.5-flash
BLINDFERENCE_NODE_GROQ_API_KEY=
BLINDFERENCE_NODE_GEMINI_API_KEY=
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=
BLINDFERENCE_NODE_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
BLINDFERENCE_NODE_COFHE_CHAIN_ID=421614
BLINDFERENCE_NODE_CALLBACK_HOST=127.0.0.1
BLINDFERENCE_NODE_CALLBACK_PORT=9101
BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=
```

### Frontend

File: [`wave2_network/packages/frontend/.env.example`](./wave2_network/packages/frontend/.env.example)

```env
VITE_ICL_API_URL=http://localhost:8000
VITE_CHAIN_ID=421614
VITE_WALLET_CONNECT_PROJECT_ID=
VITE_BLINDFERENCE_AGENT_ADDRESS=0xc9208B8aCAaD3abFc955a575719BB8F21640A6fE
VITE_BLINDFERENCE_INPUT_VAULT_ADDRESS=0x8dD7B2A9B69C76A69d33B2DF46426Cbe657a902b
```

### Contracts

File: [`wave2_network/packages/contracts/.env.example`](./wave2_network/packages/contracts/.env.example)

```env
ARBITRUM_SEPOLIA_RPC_URL=
ANVIL_RPC_URL=http://127.0.0.1:8545
PRIVATE_KEY=
ETHERSCAN_API_KEY=
ICL_SERVICE_ADDRESS=
```

Use this for Foundry deployment and verification.

## Setup Checklist

Before running the demo, confirm all of the following:

- Foundry is installed and available in your shell
- Python and Node dependencies are installed
- the ICL `.env` contains deployed contract addresses
- the ICL wallet has Sepolia ETH
- all three operator wallets have Sepolia ETH
- the node runtime has valid Groq or Gemini credentials
- the frontend points to the correct ICL base URL
- the frontend points to the deployed `BlindferenceInputVault`
- the user wallet is connected to Arbitrum Sepolia

## Installation

### Contracts

```bash
cd wave2_network/packages/contracts
forge build
forge test -vv
```

### Demo Contracts

```bash
cd wave2_network/packages/blindference-demo
forge build
forge test -vv
```

### ICL

```bash
cd wave2_network/packages/icl
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Frontend

```bash
cd wave2_network/packages/frontend
npm install --legacy-peer-deps
cp .env.example .env
```

### Node Runtime

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
pip install -r requirements.txt
npm install --legacy-peer-deps
cp .env.example .env
```

## How To Run the Demo

There are two practical modes:

- local development mode
- live Arbitrum Sepolia demo mode

For the buildathon demo, Sepolia is the intended path.

## Local Development Runbook

### 1. Start the ICL

```bash
cd wave2_network/packages/icl
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 2. Bootstrap a 3-Node Quorum

```bash
curl -s -X POST http://127.0.0.1:8000/admin/bootstrap-demo-nodes \
  -H 'Content-Type: application/json' \
  -d '{"count":3}'
```

### 3. Start Three Node Processes

Leader:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
export BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="$DEMO_OPERATOR_PRIVATE_KEY1"
export BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC"
export BLINDFERENCE_NODE_CALLBACK_PORT=9101
export BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:9101
export BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000
export BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID"
export BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY"
export BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY"
export BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false
export PYTHONPATH=src
../icl/.venv/bin/python -m blindference_node.cli start
```

Verifier 1:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
export BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="$DEMO_OPERATOR_PRIVATE_KEY2"
export BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC"
export BLINDFERENCE_NODE_CALLBACK_PORT=9102
export BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:9102
export BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000
export BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID"
export BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY"
export BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY"
export BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false
export PYTHONPATH=src
../icl/.venv/bin/python -m blindference_node.cli start
```

Verifier 2:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
export BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="$DEMO_OPERATOR_PRIVATE_KEY3"
export BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC"
export BLINDFERENCE_NODE_CALLBACK_PORT=9103
export BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:9103
export BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000
export BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID"
export BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY"
export BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY"
export BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false
export PYTHONPATH=src
../icl/.venv/bin/python -m blindference_node.cli start
```

### 4. Start the Frontend

```bash
cd wave2_network/packages/frontend
npm run dev -- --force
```

Open:

```text
http://127.0.0.1:3000
```

## Live Arbitrum Sepolia Runbook

### 1. Prepare Wallets

Fund:

- the `ICL_PRIVATE_KEY` wallet
- three operator wallets
- one user wallet for browser-side signing and permit creation

### 2. Start the ICL

```bash
cd wave2_network/packages/icl
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Bootstrap Three Funded Operators

```bash
curl -s -X POST http://127.0.0.1:8000/admin/bootstrap-demo-nodes \
  -H 'Content-Type: application/json' \
  -d '{"count":3}'
```

### 4. Start Three Node Processes

Run the same command three times, once per operator key:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<operator_private_key> \
BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC" \
BLINDFERENCE_NODE_CALLBACK_PORT=<9101-or-9102-or-9103> \
BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:<9101-or-9102-or-9103> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID" \
BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY" \
BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY" \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
../icl/.venv/bin/python -m blindference_node.cli start
```

Each node process should use:

- a distinct funded operator key
- a distinct callback port and public URL
- `BLINDFERENCE_NODE_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc`
- either Groq or Gemini API credentials

### 5. Start the Frontend

```bash
cd wave2_network/packages/frontend
npm run dev -- --force
```

### 6. Demo in the Browser

1. Open `http://127.0.0.1:3000`
2. Connect MetaMask to Arbitrum Sepolia
3. Fill the risk-scoring form
4. Submit the encrypted request
5. Watch the lifecycle:
   - input vault transaction
   - quorum preview
   - permit creation
   - leader submission
   - verifier submissions
   - accepted result
   - on-chain commitment
   - coverage state
   - mock escrow release evidence

## Expected Demo Topology

The current demo expects:

- `1` ICL coordinator
- `3` funded operator wallets
- `1` leader node process
- `2` verifier node processes

That corresponds to the default production-facing quorum:

- `1 leader + 2 verifiers`

## Deployments and Supporting Docs

Active Sepolia addresses and smoke-test transactions are tracked in:

- [DEPLOYMENT.md](./DEPLOYMENT.md)

The higher-level design summary is tracked in:

- [ARCHITECTURE.md](./ARCHITECTURE.md)

The detailed implementation and debugging handoff for future engineers / LLMs is tracked in:

- [LLM_CONTEXT.md](./LLM_CONTEXT.md)

The monorepo package-level runbook is tracked in:

- [wave2_network/README.md](./wave2_network/README.md)

## Current Status

- Core Reineira-aligned protocol contracts are deployed on Arbitrum Sepolia.
- Blindference demo contracts, including `BlindferenceInputVault`, are deployed on Arbitrum Sepolia.
- The frontend has been transplanted into the active monorepo and wired to the Wave 2 backend.
- The frontend supports live quorum progress rather than only post-commit state.
- The stack supports real CoFHE browser encryption and permit-aware request flow.
- The live CoFHE flow now stores encrypted inputs in `BlindferenceInputVault` before sharing permits are created.
- The settlement surface includes mock escrow release evidence for a complete demo narrative.

## Why Reineira and Fhenix Matter

Blindference Wave 2 stands on two important collaboration pillars:

- Reineira provides the protocol and settlement framing for verifiable, economically accountable execution.
- Fhenix / CoFHE provides the encrypted-input and selective-disclosure model that lets users share data only with the nodes that need to execute.

Together, they let Blindference demonstrate something stronger than a private inference toy example: a privacy-preserving and economically accountable AI execution workflow.

## Limitations and Demo Assumptions

- The demo uses hosted inference providers rather than locally hosted GPUs.
- The settlement surface includes a mock escrow release evidence step for demo clarity.
- Some identity, underwriting, and payout components are demo-grade rather than production-final.
- Sepolia is the intended live demo environment; local FHE mocks are secondary tooling, not the main validation path.

## References

- Reineira: https://reineira.xyz/
- Fhenix / CoFHE: https://www.fhenix.io/
- LLM / engineering handoff: [LLM_CONTEXT.md](./LLM_CONTEXT.md)
- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Deployments: [DEPLOYMENT.md](./DEPLOYMENT.md)
