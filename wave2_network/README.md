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
└── protocol/                     Upstream Reineira reference code
```

## Prerequisites

- Node.js 20+
- Python 3.11+
- Foundry
- `anvil`
- MetaMask on Arbitrum Sepolia for the live demo

## Quick Demo Run

Open separate terminals and use these relative-path commands:

```bash
npm --prefix wave2_network run dev:icl
```

```bash
npm --prefix wave2_network run dev:bootstrap
```

```bash
npm --prefix wave2_network run dev:node:leader
```

```bash
npm --prefix wave2_network run dev:node:verifier1
```

```bash
npm --prefix wave2_network run dev:node:verifier2
```

```bash
npm --prefix wave2_network run dev:frontend
```

Open `http://127.0.0.1:3000`.

To stop local demo processes:

```bash
npm --prefix wave2_network run dev:stop
```

To file a mocked dispute without using the modal:

```bash
bash wave2_network/scripts/demo/file-dispute.sh <request_id> <developer_address> "manual review requested"
```

## Vercel Deployment

Blindference Wave 2 should be deployed to Vercel as two separate monorepo projects:

- `wave2_network/packages/frontend`
- `wave2_network/packages/icl`

This matches Vercel's current monorepo guidance for independently deployed subdirectories and its FastAPI runtime support for Python backends. Sources:

- https://vercel.com/docs/monorepos
- https://vercel.com/docs/frameworks/backend/fastapi

### Frontend project

Set the Vercel project root to `wave2_network/packages/frontend`.

Included config:

- `wave2_network/packages/frontend/vercel.json`
- `wave2_network/packages/frontend/package.json`

Required Vercel environment variables:

- `VITE_ICL_API_URL=https://<your-icl-project>.vercel.app`
- `VITE_CHAIN_ID=421614`
- `VITE_WALLET_CONNECT_PROJECT_ID=<walletconnect-project-id>`
- `VITE_BLINDFERENCE_AGENT_ADDRESS=0xc9208B8aCAaD3abFc955a575719BB8F21640A6fE`
- `VITE_BLINDFERENCE_INPUT_VAULT_ADDRESS=0x8dD7B2A9B69C76A69d33B2DF46426Cbe657a902b`

Deploy from the repo root:

```bash
npm --prefix wave2_network run deploy:frontend:vercel
```

### ICL backend project

Set the Vercel project root to `wave2_network/packages/icl`.

Included config:

- `wave2_network/packages/icl/index.py`
- `wave2_network/packages/icl/vercel.json`
- `wave2_network/packages/icl/requirements.txt`

Required Vercel environment variables:

- `MONGO_URI`
- `ARBITRUM_SEPOLIA_RPC`
- `NODE_ATTESTATION_REGISTRY_ADDRESS`
- `EXECUTION_COMMITMENT_REGISTRY_ADDRESS`
- `AGENT_CONFIG_REGISTRY_ADDRESS`
- `REPUTATION_REGISTRY_ADDRESS`
- `REWARD_ACCUMULATOR_ADDRESS`
- `ICL_PRIVATE_KEY`
- `COFHE_RPC_URL`
- `COFHE_CHAIN_ID=421614`
- `DEFAULT_VERIFIER_COUNT=2`
- `HEARTBEAT_GRACE_SECONDS=3600`
- `BLINDFERENCE_ATTESTOR_ADDRESS=0x74454F689F28EfbEF6Ef9F3F14e56ac62CA8EC49`
- `BLINDFERENCE_UNDERWRITER_ADDRESS=0xcbbdcb1b42DE4Ed52f7ceD752c65652EE317B601`
- `BLINDFERENCE_AGENT_ADDRESS=0xc9208B8aCAaD3abFc955a575719BB8F21640A6fE`
- `MOCK_ORACLE_ADDRESS=0xDe9AE4b048bF320Db6492e2AfD0516392EBA05Fc`
- `DEMO_OPERATOR_PRIVATE_KEYS=<comma-separated-three-keys>`
- `MOCK_CHAIN=false`
- `DUMMY_INFERENCE_MODE=false`
- `GROQ_API_KEY` and/or `GOOGLE_API_KEY`

Deploy from the repo root:

```bash
npm --prefix wave2_network run deploy:icl:vercel
```

For a Vercel-only demo without live leader/verifier runtimes, set:

- `DUMMY_INFERENCE_MODE=true`
- optional: `DUMMY_INFERENCE_RISK_SCORE=67`

In that mode, the ICL returns a deterministic accepted result immediately after request creation and synthesizes leader/verifier submissions plus mock settlement evidence. This is useful for hosted UI demos when the real 3-node quorum is not running.

### Leader and verifier runtimes

The three node runtimes are not a fit for Vercel Functions because they are long-running worker processes with callback servers. Keep them on a VM, container host, or local machine with public callback URLs.

Important:

- If the ICL is hosted on Vercel, each node callback URL must be publicly reachable.
- `run-node.sh` now refreshes its runtime registration every 30 seconds so operator availability stays alive.
- The ICL heartbeat grace window now defaults to 1 hour.

Run them against a hosted ICL like this:

Leader:

```bash
ICL_BASE_URL=https://<your-icl-project>.vercel.app \
LEADER_CALLBACK_PUBLIC_URL=https://<leader-public-url> \
npm --prefix wave2_network run dev:node:leader
```

Verifier 1:

```bash
ICL_BASE_URL=https://<your-icl-project>.vercel.app \
VERIFIER1_CALLBACK_PUBLIC_URL=https://<verifier1-public-url> \
npm --prefix wave2_network run dev:node:verifier1
```

Verifier 2:

```bash
ICL_BASE_URL=https://<your-icl-project>.vercel.app \
VERIFIER2_CALLBACK_PUBLIC_URL=https://<verifier2-public-url> \
npm --prefix wave2_network run dev:node:verifier2
```

Re-bootstrap the funded operators against the hosted ICL after deploy:

```bash
ICL_BASE_URL=https://<your-icl-project>.vercel.app \
npm --prefix wave2_network run dev:bootstrap
```

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

Required values in `wave2_network/packages/icl/.env`:

- `ICL_PRIVATE_KEY`
- `DEMO_OPERATOR_PRIVATE_KEYS` or `DEMO_OPERATOR_PRIVATE_KEY1/2/3`
- `GROQ_API_KEY` or `GOOGLE_API_KEY`

The public Sepolia contract addresses can stay on the defaults from `.env.example`.

### Frontend

```bash
cd wave2_network/packages/frontend
npm install --legacy-peer-deps
cp .env.example .env
```

Recommended values in `wave2_network/packages/frontend/.env`:

- `VITE_ICL_API_URL=http://127.0.0.1:8000`
- `VITE_CHAIN_ID=421614`
- `VITE_WALLET_CONNECT_PROJECT_ID=<your_walletconnect_project_id>`

The deployed agent and input vault addresses already exist in `.env.example`.

### Node Runtime

```bash
cd wave2_network/packages/node-reineira
source ../icl/.venv/bin/activate
pip install -r requirements.txt
npm install --legacy-peer-deps
cp .env.example .env
```

The demo scripts source `wave2_network/packages/icl/.env`, so you do not need to maintain a separate runtime `.env` for normal local usage.

## Local Demo Commands

Use the quick demo scripts above for the normal flow. The detailed commands below remain as a reference.

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
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="$DEMO_OPERATOR_PRIVATE_KEY1" \
BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC" \
BLINDFERENCE_NODE_CALLBACK_PORT=9101 \
BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:9101 \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID" \
BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY" \
BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY" \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
../icl/.venv/bin/python -m blindference_node.cli start
```

Verifier 1:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="$DEMO_OPERATOR_PRIVATE_KEY2" \
BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC" \
BLINDFERENCE_NODE_CALLBACK_PORT=9102 \
BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:9102 \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID" \
BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY" \
BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY" \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
../icl/.venv/bin/python -m blindference_node.cli start
```

Verifier 2:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="$DEMO_OPERATOR_PRIVATE_KEY3" \
BLINDFERENCE_NODE_RPC_URL="$ARBITRUM_SEPOLIA_RPC" \
BLINDFERENCE_NODE_CALLBACK_PORT=9103 \
BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL=http://127.0.0.1:9103 \
BLINDFERENCE_NODE_ICL_BASE_URL=http://127.0.0.1:8000 \
BLINDFERENCE_NODE_COFHE_CHAIN_ID="$COFHE_CHAIN_ID" \
BLINDFERENCE_NODE_GROQ_API_KEY="$GROQ_API_KEY" \
BLINDFERENCE_NODE_GEMINI_API_KEY="$GOOGLE_API_KEY" \
BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false \
PYTHONPATH=src \
../icl/.venv/bin/python -m blindference_node.cli start
```

### 7. Start the Frontend

```bash
cd wave2_network/packages/frontend
npm run dev -- --force
```

Open `http://127.0.0.1:3000`.

## Live Sepolia Demo Commands

Use the quick demo scripts above for the normal flow. The detailed commands below remain as a reference.

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
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<leader_private_key> \
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

Verifier 1:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<verifier_one_private_key> \
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

Verifier 2:

```bash
cd wave2_network/packages/node-reineira
set -a
source ../icl/.env
set +a
BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY=<verifier_two_private_key> \
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

### 4. Start the Frontend

```bash
cd wave2_network/packages/frontend
npm run dev -- --force
```

### 5. Browser Demo Flow

1. Open `http://127.0.0.1:3000`
2. Connect MetaMask on Arbitrum Sepolia
3. Fill in the risk fields
4. Submit the encrypted request
5. Watch:
   - input vault transaction
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
- Disputes are also mocked for the demo: filing a dispute adds visible mock dispute submission and resolution evidence to the request metadata.
- Deployment addresses are tracked in [../DEPLOYMENT.md](../DEPLOYMENT.md).
