# Blindference

Confidential AI inference protocol. Off-chain plaintext inference on selected operators (CoFHE-permitted), on-chain commit-reveal verification + escalation arbitration, settled through Reineira escrow with optional underwriting on agent outputs.

## Architecture

Reineira-side contracts are highlighted in **orange**. Blindference-side contracts in **blue**. Off-chain actors are gray.

```mermaid
flowchart TB
    subgraph Reineira[" 🟧 Reineira protocol (settlement / identity / coverage) "]
        AIA[AgentInvocationAdapter<br/><i>kicks off invocation</i>]
        AID[AgentIdentityRegistry<br/><i>ERC-8004</i>]
        ESC[(IEscrow<br/><i>holds funds</i>)]
        QAR[QuorumAttestedResolver<br/><i>fires release gates</i>]
        OSM[OperatorSlashingManager<br/><i>slashes on fraud</i>]
    end

    subgraph Blindference[" 🟦 Blindference protocol (off-chain compute / on-chain commitments) "]
        NAR[NodeAttestationRegistry]
        ACR[AgentConfigRegistry]
        ECR[ExecutionCommitmentRegistry]
        ASR[ArbiterSelectionRegistry]
        REP[ReputationRegistry]
        ACC[RewardAccumulator]
    end

    subgraph Nodes[" ⚪ Off-chain nodes "]
        EX[Executor]
        CV[Cross-verifier]
        ARB[Arbiters x5]
    end

    User([Client / Trader]) -- invoke --> AIA
    AIA -- dispatch --> ECR
    AIA -. funds escrow .-> ESC
    AID -. resolves agentId → wallet .-> ACR

    ECR -- task --> EX
    ECR -- task --> CV
    EX -- commit + reveal --> ECR
    CV -- commit + reveal --> ECR

    ECR -- VERIFIED bytes32 --> QAR
    QAR -- release --> ESC

    ECR -. ESCALATED .-> ASR
    ASR -- VRF select --> ARB
    ARB -- commit + reveal --> ASR
    ASR -- majority --> REP
    REP -- guilty? .-> ACC
    REP -- evidence --> OSM

    NAR -. attestation requirements .-> ASR
    ACR -. slot config .-> ECR

    ACC -- cycle-end release --> ESC

    classDef reineira fill:#fff4e0,stroke:#c97a00,color:#1a1a1a,stroke-width:2px
    classDef blindfer fill:#e6f4ff,stroke:#1d6fb8,color:#1a1a1a,stroke-width:2px
    classDef nodes fill:#f5f5f5,stroke:#666,color:#1a1a1a
    class AIA,AID,ESC,QAR,OSM reineira
    class NAR,ACR,ECR,ASR,REP,ACC blindfer
    class EX,CV,ARB nodes
```

### What Reineira owns vs. what Blindference owns

| Reineira (orange) | Blindference (blue) |
|---|---|
| `AgentInvocationAdapter` — entrypoint that opens an escrow + emits invocation events | `ECR` — on-chain commit-reveal verification |
| `IEscrow` — holds the funds; never released until gates fire | `ASR` — VRF-based arbiter selection on disputes |
| `QuorumAttestedResolver` — fires release gates after verdict + attestation | `ReputationRegistry` — tracks per-cycle fraud, gates `RewardAccumulator.release` |
| `AgentIdentityRegistry` — ERC-8004 identity lookup | `RewardAccumulator` — per-cycle accrual, releases via Reineira `IEscrow` |
| `OperatorSlashingManager` — consumes Blindference fraud evidence to slash GOV stake | `NodeAttestationRegistry`, `AgentConfigRegistry` — operator + agent on-chain config |
| All money flow | All execution + verification |

## Packages

| Path | Stack | Purpose |
|---|---|---|
| [`packages/contracts`](packages/contracts) | Solidity (Foundry) | Protocol contracts: identity, attestations, commit-reveal, arbitration, reputation, rewards |
| [`packages/node`](packages/node) | Python (DDD) | Installable node runtime — `pip install blindference-node` |
| [`packages/examples-trading-signal`](packages/examples-trading-signal) | Solidity | Reference vertical: insured AI trading signals |
| [`packages/examples-trading-signal-sdk`](packages/examples-trading-signal-sdk) | TypeScript (viem) | SDK for the trading signal example |

## Quick start

```bash
pnpm install
pnpm -r build
pnpm -r test          # 122 tests across 3 Solidity packages + TS SDK
```

Deploy a Trading Signal Agent end-to-end:

```bash
cd packages/examples-trading-signal
forge script script/DeployTradingAgent.s.sol \
  --rpc-url $ARBITRUM_SEPOLIA_RPC \
  --private-key $DEPLOYER_KEY \
  --broadcast
```

## Trading Signal Agent — insured-AI flow

Each participant is labeled by which protocol owns it: 🟧 Reineira, 🟦 Blindference, 🟩 trading vertical, ⚪ off-chain.

```mermaid
sequenceDiagram
    autonumber
    actor Trader as ⚪ Trader
    participant Agent as ⚪ Agent wallet
    participant ECR as 🟦 ExecutionCommitmentRegistry
    participant E as ⚪ Executor node
    participant V as ⚪ Cross-verifier node
    participant TSA as 🟩 TradingSignalAttestor
    participant TLU as 🟩 TradingLossUnderwriter
    participant Oracle as 🟩 PriceOracle
    participant Esc as 🟧 Reineira IEscrow

    Trader->>Agent: request signal (asset, validity)
    Agent->>ECR: dispatch (invocationId, executor, crossVerifier)

    par
        ECR->>E: dispatched task
        E->>E: decrypt evidence + run model
    and
        ECR->>V: dispatched task
        V->>V: decrypt evidence + re-run model
    end

    E->>ECR: commit(hash) → reveal(salt, output)
    V->>ECR: commit(hash) → reveal(salt, output)
    ECR-->>Agent: status = VERIFIED, executorOutput = signalHash

    Agent->>TSA: commitSignal(payload)
    TSA->>ECR: read invocation.executorOutput
    TSA->>TSA: keccak(payload) == executorOutput ✓
    TSA-->>Trader: SignalCommitted event (BUY/SELL/HOLD + confidence)

    Trader->>TLU: purchaseCoverage(invocationId, $1000, escrowId)
    Note over TLU,Esc: Premium escrowed via Reineira IEscrow (out of band)

    Note over Trader,Oracle: Time passes; trader acts on signal off-chain

    Trader->>TLU: claimLoss(invocationId)
    TLU->>TSA: signalOf(invocationId)
    TLU->>Oracle: latestAnswer(asset)
    TLU->>TLU: lossBps = computeLoss(signal, currentPrice)
    alt lossBps >= threshold
        TLU->>Esc: release(escrowId, trader, payout)
        Esc-->>Trader: 💰 payout
        TLU-->>Trader: ClaimPaid event
    else lossBps < threshold
        TLU-->>Trader: revert LossBelowThreshold
    end
```

The trading vertical (🟩) is the only thing a developer writes for a new agent type. Everything else is reusable Blindference + Reineira primitives.

## Tests

| Package | Count | Tooling |
|---|---|---|
| `@blindference/contracts` | 98 | Foundry |
| `@blindference/examples-trading-signal` | 9 | Foundry |
| `@blindference/examples-trading-signal-sdk` | 15 | Vitest |
| **Total** | **122** | |

```bash
pnpm -r test         # all green
pnpm -r format       # forge fmt + prettier (TS)
pnpm -r lint         # solhint + tsc --noEmit
```

## Tech debt

Reineira protocol is currently a private repo. Blindference vendors three Reineira artifacts (`TestnetCoreBase`, `FHEMeta`, `IEscrow`) under [`packages/contracts/contracts/_reineira_stubs/`](packages/contracts/contracts/_reineira_stubs/). At chaosenet (Reineira public testnet launch), see [`TECH-DEBT.md`](packages/contracts/contracts/interfaces/TECH-DEBT.md) for the migration: `forge install reineira-os/shared` then delete the stub directory.

## License

BUSL-1.1.
