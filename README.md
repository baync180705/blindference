# Blindference

Blindference Wave 2 is the SLA layer for Web3 AI: off-chain inference runs across a confidential node quorum, and the financial outcome settles on Arbitrum Sepolia through the Reineira protocol stack.

The active Wave 2 buildathon work lives in [wave2_network](./wave2_network). Legacy Wave 1 Fhenix code remains in this repository for reference, but the current demo, contracts, ICL backend, and operator runtime are all under `wave2_network/`.

## Current Status

- Core Reineira protocol contracts are deployed and verified on Arbitrum Sepolia.
- The Blindference demo vertical is deployed and verified on Arbitrum Sepolia.
- The ICL backend completed a live Sepolia smoke test with a `1 leader + 1 verifier` quorum.
- The frontend can request inference, track quorum status, and show the accepted result/dispute state.
- A Groq/Gemini-ready node runtime exists for buildathon demos, with mock mode available for local development.

Deployment details and live addresses are in [DEPLOYMENT.md](./DEPLOYMENT.md).

## Repository Layout

```text
blindference/
├── wave2_network/              Active Wave 2 monorepo
│   ├── packages/contracts/     Reineira core protocol contracts in Foundry form
│   ├── packages/blindference-demo/
│   │                           Blindference demo vertical contracts
│   ├── packages/icl/           FastAPI inference coordination layer
│   ├── packages/frontend/      React + Vite demo frontend
│   ├── packages/node-reineira/ Demo operator runtime
│   ├── packages/sdk/           SDK scaffold
│   └── packages/mcp-server/    MCP scaffold
├── backend/                    Legacy Wave 1 backend
├── frontend/                   Legacy Wave 1 frontend
├── fhenix_inference/           Legacy Wave 1 contracts
└── README.md
```

## Quick Start

Use the detailed setup guide in [wave2_network/README.md](./wave2_network/README.md).

Typical local flow:

1. Start `anvil`.
2. Deploy `packages/contracts` and `packages/blindference-demo` with Foundry.
3. Start the ICL backend from `packages/icl`.
4. Start the React frontend from `packages/frontend`.
5. Run the demo node runtime from `packages/node-reineira`.

## What Is Still Open From The Reineira Side

These are the remaining partner-owned or joint integration seams we still treat as non-final:

- Replace `MockAgentIdentityRegistry` with the production identity / ERC-8004-aligned registry.
- Replace `MockEscrowReleaser` with the real settlement and escrow release path.
- Replace the demo price oracle path with the intended production oracle / policy data source.
- Harden the underwriter + dispute flow beyond the demo policy assumptions.
- Finish production-grade operator lifecycle tooling around attestations, rewards, and reputation automation.

## Security Notes Before Push

- Real `.env` files are gitignored; only `.env.example` files should be committed.
- The repository currently contains public Anvil default keys in code defaults for local testing. Those are not private funds, but production or funded keys should only live in ignored `.env` files.
- If you are about to push, double-check `git status` and make sure no real `.env`, cache, broadcast, or backup folders are staged.
