# Blindference Wave 2

Blindference Wave 2 is the SLA layer for Web3 AI. A user encrypts numeric risk-scoring inputs with CoFHE, the ICL assigns a `1 leader + 2 verifier` quorum, each node decrypts locally under user-granted permits, inference runs off-chain through Groq or Gemini, and the result commitment settles on Arbitrum Sepolia through the Reineira protocol stack.

The active codebase is now entirely under [wave2_network](./wave2_network). The old root-level Wave 1 apps have been removed so this repository is ready to push as a single Wave 2 monorepo.

## Repo Layout

```text
blindference/
├── ARCHITECTURE.md
├── DEPLOYMENT.md
├── README.md
└── wave2_network/
    ├── packages/contracts/           Reineira core protocol contracts
    ├── packages/blindference-demo/   Blindference demo contracts
    ├── packages/icl/                 FastAPI inference coordination layer
    ├── packages/frontend/            BF demo frontend, wired to live Wave 2 APIs
    ├── packages/node-reineira/       Leader / verifier node runtime
    ├── packages/fhe-mocks/           Optional local CoFHE mock node
    ├── packages/sdk/
    ├── packages/mcp-server/
    └── protocol/                     Upstream Reineira protocol reference
```

## Quick Start

Use the full runbook in [wave2_network/README.md](./wave2_network/README.md).

For the live demo path, the normal sequence is:

1. Start the ICL from `wave2_network/packages/icl`.
2. Bootstrap 3 demo operators through the ICL admin route.
3. Start 3 node daemons from `wave2_network/packages/node-reineira`, one per operator key.
4. Start the BF frontend from `wave2_network/packages/frontend`.
5. Open the app, connect MetaMask on Arbitrum Sepolia, submit a risk request, and watch the quorum settle.

## Current Demo State

- Core protocol contracts are deployed on Arbitrum Sepolia.
- Blindference demo contracts are deployed on Arbitrum Sepolia.
- The BF frontend design has been transplanted into `wave2_network/packages/frontend` and wired to the live Wave 2 APIs.
- The frontend now shows in-flight leader and verifier progress before final commitment.
- The demo includes a mock escrow release surface after accepted risk scoring so the UI has complete settlement evidence for recording.

## Docs

- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Deployments: [DEPLOYMENT.md](./DEPLOYMENT.md)
- Monorepo runbook: [wave2_network/README.md](./wave2_network/README.md)
