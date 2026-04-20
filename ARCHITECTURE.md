# Architecture

## Overview

Blindference Wave 2 is a confidential AI execution pipeline with economic verification and on-chain settlement visibility.

In the current demo:

1. The frontend encrypts loan-risk features with CoFHE in the user's wallet.
2. The ICL previews and assigns a quorum of `1 leader + 2 verifiers`.
3. The frontend creates one CoFHE sharing permit per selected node and submits the encrypted payload.
4. Each node decrypts locally, runs inference through Groq or Gemini, and submits a result or verifier verdict.
5. The ICL aggregates the quorum, commits the final result hash to `ExecutionCommitmentRegistry`, and records demo settlement metadata.
6. The frontend renders the full lifecycle: assignment, execution, verification, commitment, coverage, and mock escrow release.

## System Diagram

```mermaid
flowchart LR
    U[User Wallet] --> F[Blindference Frontend]
    F -->|Encrypt features with CoFHE| C[(Encrypted Payload)]
    F -->|Quorum preview request| ICL[ICL / FastAPI]
    ICL -->|Select leader + verifiers| Q[Quorum Assignment]
    F -->|Create one permit per node| P[CoFHE Sharing Permits]
    C --> ICL
    P --> ICL

    ICL --> L[Leader Node]
    ICL --> V1[Verifier Node 1]
    ICL --> V2[Verifier Node 2]

    L -->|Decrypt locally + infer| AI1[Groq / Gemini]
    V1 -->|Decrypt locally + verify| AI2[Groq / Gemini]
    V2 -->|Decrypt locally + verify| AI3[Groq / Gemini]

    L -->|Leader result| ICL
    V1 -->|Verifier verdict| ICL
    V2 -->|Verifier verdict| ICL

    ICL -->|Commit accepted result| ECR[ExecutionCommitmentRegistry]
    ICL -->|Coverage / settlement metadata| DEMO[Blindference Demo Contracts]

    ECR --> UI[Frontend Status + Evidence]
    DEMO --> UI
```

## Request Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant ICL
    participant Leader
    participant Verifier1
    participant Verifier2
    participant Chain as Arbitrum Sepolia

    User->>Frontend: Enter loan features
    Frontend->>Frontend: Encrypt with CoFHE
    Frontend->>ICL: GET /v1/inference/quorum-preview
    ICL-->>Frontend: leader + verifier addresses
    Frontend->>Frontend: Create one sharing permit per node
    Frontend->>ICL: POST encrypted request + permits
    ICL->>Chain: register task
    ICL->>Leader: encrypted payload + leader permit
    ICL->>Verifier1: encrypted payload + verifier permit
    ICL->>Verifier2: encrypted payload + verifier permit
    Leader->>Leader: decrypt locally
    Verifier1->>Verifier1: decrypt locally
    Verifier2->>Verifier2: decrypt locally
    Leader->>Leader: run inference
    Verifier1->>Verifier1: run verification
    Verifier2->>Verifier2: run verification
    Leader-->>ICL: leader result
    Verifier1-->>ICL: verifier verdict
    Verifier2-->>ICL: verifier verdict
    ICL->>ICL: aggregate quorum
    ICL->>Chain: commit accepted result
    Chain-->>Frontend: commitment visible on-chain
```

## Quorum Topology

```mermaid
flowchart TB
    subgraph Coordinator
        ICL[Inference Coordination Layer]
    end

    subgraph Quorum["Execution Quorum"]
        L[Leader]
        V1[Verifier 1]
        V2[Verifier 2]
    end

    subgraph Inference
        G[Groq]
        GM[Gemini]
    end

    ICL --> L
    ICL --> V1
    ICL --> V2

    L --> G
    L --> GM
    V1 --> G
    V1 --> GM
    V2 --> G
    V2 --> GM

    L -->|result| ICL
    V1 -->|verdict| ICL
    V2 -->|verdict| ICL
```

## Main Components

### Frontend

Location: `wave2_network/packages/frontend`

- React/Vite application used as the buildathon demo UI
- Wallet connection via `wagmi`
- Real CoFHE browser client via `@cofhe/sdk`
- Quorum preview before submission
- Multi-recipient permit creation for leader and verifiers
- Live request polling and visual quorum progress
- Coverage, dispute, and settlement evidence display

### ICL

Location: `wave2_network/packages/icl`

- FastAPI coordination backend
- Quorum preview and task creation
- Permit-aware request intake
- Task registration on Arbitrum Sepolia
- Leader result and verifier verdict ingestion
- Quorum aggregation and final commitment
- Demo metadata for coverage and visible escrow release

### Node Runtime

Location: `wave2_network/packages/node-reineira`

- One process per operator key
- Role detection: leader or verifier
- CoFHE decrypt path using user-shared permits
- Hosted inference via Groq or Gemini
- Result hashing and callback submission to the ICL

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

## Package Boundary Diagram

```mermaid
flowchart LR
    FE[packages/frontend] --> ICL[packages/icl]
    ICL --> NR[packages/node-reineira]
    ICL --> CORE[packages/contracts]
    ICL --> DEMO[packages/blindference-demo]
    NR --> FHE[CoFHE RPC]
    NR --> LLM[Groq / Gemini]
    FE --> FHE
```

## Privacy Model

- The ICL never receives plaintext loan features.
- Ciphertexts are created in the browser.
- The user shares CoFHE permits only with the selected quorum members.
- Each node decrypts locally with its own wallet-scoped permit.
- Verifiers work from the same encrypted payload, not from a plaintext copy from the coordinator.

## Demo Settlement Model

The buildathon demo uses:

- real on-chain execution commitment on Arbitrum Sepolia
- real quorum selection and result aggregation
- real coverage and dispute surfaces in the UI
- a mock escrow release evidence step after accepted scoring so the demo shows the full economic lifecycle without requiring a production escrow releaser

## Deployment View

```mermaid
flowchart TB
    subgraph Browser
        FE[Frontend]
        W[User Wallet]
    end

    subgraph Backend
        ICL[ICL]
        N1[Node Runtime - Leader]
        N2[Node Runtime - Verifier 1]
        N3[Node Runtime - Verifier 2]
    end

    subgraph External
        COFHE[CoFHE Testnet RPC]
        ARB[Arbitrum Sepolia]
        LLM[Groq / Gemini APIs]
    end

    W --> FE
    FE --> ICL
    FE --> COFHE
    ICL --> ARB
    ICL --> N1
    ICL --> N2
    ICL --> N3
    N1 --> COFHE
    N2 --> COFHE
    N3 --> COFHE
    N1 --> LLM
    N2 --> LLM
    N3 --> LLM
```

## Package Boundaries

```text
wave2_network/
├── packages/contracts/         Core protocol
├── packages/blindference-demo/ Demo contracts
├── packages/icl/               Coordination backend
├── packages/frontend/          User-facing BF app
├── packages/node-reineira/     Quorum node runtime
├── packages/fhe-mocks/         Optional local FHE helpers
└── protocol/                   Reineira upstream reference
```

## Remaining Non-Final Pieces

- Production identity / ERC-8004 registry replacement for mocks
- Production escrow release path instead of demo settlement metadata
- Production oracle and policy hardening for disputes and underwriting
- Full operator lifecycle automation for reputation, rewards, and staking
