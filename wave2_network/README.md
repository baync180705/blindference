# Wave 2 Monorepo

This is the active Blindference Wave 2 monorepo.

## Packages

```text
wave2_network/
├── packages/contracts/           Reineira core protocol contracts
├── packages/blindference-demo/   Blindference demo contracts
├── packages/icl/                 FastAPI coordination layer
├── packages/frontend/            BF demo frontend
├── packages/node-reineira/       Leader / verifier runtime
├── packages/fhe-mocks/           Optional local CoFHE mock node
├── packages/sdk/
├── packages/mcp-server/
└── protocol/                     Upstream Reineira reference code
```

## Prerequisites

- Node.js 20+
- Python 3.11+
- Foundry
- `anvil`
- MetaMask on Arbitrum Sepolia for the live demo

## Install

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

## Local Demo Commands

### 1. Start Anvil

```bash
anvil --port 8545
```

### 2. Deploy Core Protocol

```bash
cd wave2_network/packages/contracts
forge script script/Deploy.s.sol:DeployScript --rpc-url http://127.0.0.1:8545 --broadcast
```

### 3. Deploy Blindference Demo Contracts

```bash
cd wave2_network/packages/blindference-demo
forge script script/DeployBlindferenceAgent.s.sol:DeployBlindferenceAgentScript --rpc-url http://127.0.0.1:8545 --broadcast
```

### 4. Start the ICL

```bash
cd wave2_network/packages/icl
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 5. Bootstrap 3 Demo Operators

```bash
curl -s -X POST http://127.0.0.1:8000/admin/bootstrap-demo-nodes \
  -H 'Content-Type: application/json' \
  -d '{"count":3}'
```

### 6. Start the 3 Node Daemons

Leader:

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<leader_private_key> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
PYTHONPATH=src \
python -m blindference_node.cli start
```

Verifier 1:

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<verifier_one_private_key> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
PYTHONPATH=src \
python -m blindference_node.cli start
```

Verifier 2:

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<verifier_two_private_key> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
PYTHONPATH=src \
python -m blindference_node.cli start
```

### 7. Start the Frontend

```bash
cd wave2_network/packages/frontend
npm run dev
```

Open `http://localhost:3000`.

## Live Sepolia Demo Commands

### 1. Start the ICL

```bash
cd wave2_network/packages/icl
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 2. Bootstrap 3 Funded Operators

```bash
curl -s -X POST http://127.0.0.1:8000/admin/bootstrap-demo-nodes \
  -H 'Content-Type: application/json' \
  -d '{"count":3}'
```

### 3. Start Leader and Verifiers

Leader:

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<leader_private_key> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
python -m blindference_node.cli start
```

Verifier 1:

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<verifier_one_private_key> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
python -m blindference_node.cli start
```

Verifier 2:

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<verifier_two_private_key> \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
python -m blindference_node.cli start
```

### 4. Start the Frontend

```bash
cd wave2_network/packages/frontend
npm run dev
```

### 5. Browser Demo Flow

1. Open `http://localhost:3000`
2. Connect MetaMask on Arbitrum Sepolia
3. Fill in the risk fields
4. Submit the encrypted request
5. Watch:
   - leader assignment
   - verifier progress
   - accepted risk score
   - result commitment evidence
   - coverage state
   - mock escrow release evidence

## Notes

- The frontend now uses the BF design system from the original `bf` app, but it is wired to the real Wave 2 APIs.
- The app expects `1 leader + 2 verifiers`.
- The demo uses a visible mock escrow release after accepted scoring so the full economic lifecycle is present in recordings.
- Deployment addresses are tracked in [../DEPLOYMENT.md](../DEPLOYMENT.md).
