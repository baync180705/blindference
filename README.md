# Blindference

`blindference` is the private application repository. It now contains:

- `fhenix_inference/` for smart contracts, Hardhat config, deployment scripts, and compiled artifacts
- `backend/` for the FastAPI dumb-pipe service and model status bridge
- `frontend/` for the React client, wallet flow, and browser-side encrypted inference UX

## Repo layout

```text
blindference/
├── backend/
├── frontend/
└── fhenix_inference/
```

## Environment files

### Contracts

Create `fhenix_inference/.env` from `fhenix_inference/.env.example`:

```env
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
DEPLOYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
FEE_TREASURY=0xYOUR_WALLET_ADDRESS
```

Deploy from:

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/fhenix_inference
npm install
npx hardhat compile
npx hardhat run scripts/deploy.ts --network sepolia
```

### Frontend

Create `frontend/.env.local` from `frontend/.env.example`:

```env
VITE_BLIND_INFERENCE_ADDRESS=0x...
VITE_INFERENCE_ENGINE_ADDRESS=0x...
VITE_MODEL_REGISTRY_ADDRESS=0x...
VITE_PAYMENT_ESCROW_ADDRESS=0x...
VITE_PAYMENT_TOKEN_ADDRESS=0x...
VITE_DEFAULT_REQUEST_ID=1
```

These addresses come from the `fhenix_inference` deploy output.

### Backend

Create `backend/.env` with at least:

```env
MONGO_URI=mongodb://localhost:27017
```

## Frontend ABI source

The frontend now imports contract artifacts directly from:

- `fhenix_inference/artifacts/contracts/...`

There is no longer any cross-repo ABI export step.
