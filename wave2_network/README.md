# Blindference Wave 2

This monorepo contains the active Blindference Wave 2 buildathon stack:

- Reineira core protocol contracts in Foundry form
- Blindference demo vertical contracts
- the ICL FastAPI backend
- the React demo frontend
- the demo operator runtime

## Packages

```text
wave2_network/
├── packages/contracts/           Core protocol contracts
├── packages/blindference-demo/   Blindference demo contracts
├── packages/blindference-demo-sdk/
├── packages/icl/                 Inference Coordination Layer
├── packages/frontend/            Demo UI
├── packages/node-reineira/       Demo operator runtime
├── packages/sdk/
└── packages/mcp-server/
```

## Prerequisites

- Node.js 20+
- Python 3.11+
- Foundry
- Anvil

## Local Development

### 1. Start a local chain

```bash
anvil
```

### 2. Deploy the core protocol

```bash
cd packages/contracts
npm install
forge build
forge test -vv
forge script script/Deploy.s.sol:DeployScript --rpc-url http://127.0.0.1:8545 --broadcast
```

### 3. Deploy the Blindference demo vertical

```bash
cd ../blindference-demo
npm install
forge build
forge test -vv
forge script script/DeployBlindferenceAgent.s.sol:DeployBlindferenceAgentScript --rpc-url http://127.0.0.1:8545 --broadcast
```

### 4. Run the ICL backend

```bash
cd ../icl
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Important:

- `DEMO_OPERATOR_PRIVATE_KEYS` should be a comma-separated list of funded operator keys.
- `ICL_SERVICE_PRIVATE_KEY` must also have gas on the target network.

### 5. Run the frontend

```bash
cd ../frontend
npm install
cp .env.example .env
npm run dev
```

### 6. Run the demo node runtime

```bash
cd ../node-reineira
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
blindference-node status
blindference-node start
```

## Sepolia Deployment

Live Sepolia addresses and the successful smoke-test transaction are recorded in [../DEPLOYMENT.md](../DEPLOYMENT.md).

## Open Reineira Integration Items

- Swap `MockAgentIdentityRegistry` for the production identity registry.
- Swap `MockEscrowReleaser` for the production reward / settlement release path.
- Replace the mock oracle path with the intended production oracle wiring.
- Harden the insurance + dispute lifecycle beyond the buildathon demo scope.
- Finalize operator lifecycle automation around attestations, rewards, and reputation.
