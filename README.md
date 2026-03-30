# Blindference

`blindference` is the private application repository for the product layer of the system.

This repo owns:

- Fhenix/CoFHE smart contracts and deployment scripts
- the FastAPI backend used as the off-chain routing layer
- the React frontend for AI labs, hospitals, and marketplace users
- wallet, permit, encryption, and decryption UX

The off-chain Rust encrypted ML engine lives separately in the `PPML` repository.

## Repository layout

```text
blindference/
├── backend/            # FastAPI router, GridFS bridge, model status endpoint
├── frontend/           # React + Vite application
├── fhenix_inference/   # Hardhat workspace, contracts, deploy scripts, artifacts
└── README.md
```

## What goes where

### `fhenix_inference/`

Use this directory for:

- Solidity contracts
- Hardhat config
- Sepolia deployment
- contract artifacts

### `backend/`

Use this directory for:

- dataset upload/download routing
- MongoDB / GridFS integration
- bridging the frontend to off-chain model export status

### `frontend/`

Use this directory for:

- wallet connect
- CoFHE/Fhenix browser encryption
- AI lab model registration
- hospital inference submission
- permit-based result decryption

## Environment files

There are three separate env locations in this repo.

### 1. Contract deployment env

Create:

- [`blindference/fhenix_inference/.env`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/fhenix_inference/.env)

From:

- [`blindference/fhenix_inference/.env.example`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/fhenix_inference/.env.example)

Example:

```env
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
DEPLOYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
FEE_TREASURY=0xYOUR_WALLET_ADDRESS
```

Meaning:

- `SEPOLIA_RPC_URL`: Ethereum Sepolia RPC endpoint
- `DEPLOYER_PRIVATE_KEY`: deployer wallet private key with `0x` prefix
- `FEE_TREASURY`: address receiving platform fees

### 2. Frontend env

Create:

- [`blindference/frontend/.env.local`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend/.env.local)

From:

- [`blindference/frontend/.env.example`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend/.env.example)

Example:

```env
VITE_BLIND_INFERENCE_ADDRESS=0xYOUR_BLIND_INFERENCE_ADDRESS
VITE_INFERENCE_ENGINE_ADDRESS=0xYOUR_INFERENCE_ENGINE_ADDRESS
VITE_MODEL_REGISTRY_ADDRESS=0xYOUR_MODEL_REGISTRY_ADDRESS
VITE_PAYMENT_ESCROW_ADDRESS=0xYOUR_PAYMENT_ESCROW_ADDRESS
VITE_PAYMENT_TOKEN_ADDRESS=0xYOUR_PAYMENT_TOKEN_ADDRESS
VITE_DEFAULT_MODEL_ID=1
VITE_DEFAULT_REQUEST_ID=1
```

Meaning:

- `VITE_BLIND_INFERENCE_ADDRESS`: main external inference entrypoint used by the portal
- `VITE_INFERENCE_ENGINE_ADDRESS`: explicit inference engine address
- `VITE_MODEL_REGISTRY_ADDRESS`: model registry contract address
- `VITE_PAYMENT_ESCROW_ADDRESS`: escrow contract address
- `VITE_PAYMENT_TOKEN_ADDRESS`: BFHE/mock payment token address
- `VITE_DEFAULT_MODEL_ID`: default model selection in the portal
- `VITE_DEFAULT_REQUEST_ID`: optional fallback request id for demos

These values should come from the contract deploy output.

### 3. Backend env

Create:

- [`blindference/backend/.env`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/backend/.env)

Example:

```env
MONGO_URI=mongodb://localhost:27017
```

If you are using MongoDB Atlas, use the full Atlas connection string instead.

## Install instructions

### Contracts

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/fhenix_inference
npm install
```

### Backend

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend
npm install
```

## Contract deployment

Deploy to Sepolia from the Hardhat workspace:

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/fhenix_inference
npx hardhat compile
npx hardhat run scripts/deploy.ts --network sepolia
```

After deployment:

1. copy the printed addresses
2. place them into [`blindference/frontend/.env.local`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend/.env.local)
3. restart the frontend dev server

## Running the stack

Use separate terminals.

### Terminal 1: Backend

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Backend health check:

- `http://127.0.0.1:8000/health`

### Terminal 2: Frontend

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend
npm run dev -- --force
```

Open the URL printed by Vite.

### Optional: Re-deploy contracts

If contracts changed:

```bash
cd /home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/fhenix_inference
npx hardhat run scripts/deploy.ts --network sepolia
```

Then update [`blindference/frontend/.env.local`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend/.env.local) with the new addresses.

## Sepolia wallet setup

The frontend is currently configured for Ethereum Sepolia.

Make sure:

- MetaMask is on Sepolia
- the connected wallet has Sepolia ETH for gas
- the hospital wallet has enough payment tokens for inference

## End-to-end usage flow

### AI Lab flow

1. Open the frontend
2. Connect MetaMask with the AI lab account
3. Go to `Lab`
4. Register the AI lab profile if prompted
5. Register the encrypted model

What happens:

- the browser encrypts model weights and bias with the Fhenix/CoFHE client
- the encrypted model is registered on-chain
- the model gets a `modelId`

### Hospital flow

1. Switch MetaMask to a different hospital account
2. Open `Market` to view available models
3. Open `Portal`
4. Choose the model id
5. Enter patient inputs
6. Approve BFHE token spend if needed
7. Submit inference
8. Click `Decrypt Result`
9. Sign the permit request

What happens:

- the hospital browser encrypts the patient datapoint locally
- the contract computes over encrypted inputs and encrypted weights
- the result handle is ACL-granted to the requesting wallet
- the hospital signs a permit and decrypts the score off-chain in the UI

## Frontend ABI source

The frontend imports contract artifacts directly from:

- `fhenix_inference/artifacts/contracts/...`

There is no separate cross-repo ABI export step anymore.

## Troubleshooting

### Wallet connects but FHE client fails

Check:

- MetaMask is on Sepolia
- the contract addresses in [`frontend/.env.local`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend/.env.local) are the latest deployed ones
- you restarted Vite after changing env files

### Model registration reverts with `AI lab not registered`

Use the Lab Dashboard with the AI lab wallet first. The wallet must register as a lab before uploading a model.

### Inference works but decrypt fails

Check:

- the same hospital wallet that submitted the request is trying to decrypt
- the frontend was restarted after CoFHE SDK or env changes
- the result handle came from the current deployed inference contract

### Frontend loads slowly

This app uses browser-side FHE, wasm, workers, and permit storage. First load in dev mode is heavier than a typical React app. The current code defers CoFHE client initialization until it is actually needed.

## Security notes

- Never commit real private keys to git
- Keep [`frontend/.env.local`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/frontend/.env.local) local-only
- Keep [`backend/.env`](/home/abhieren/Drive/Projects/Buildathon/Fhenix/blindference/backend/.env) local-only
- Rotate any private key or Mongo credential that has been exposed in logs, screenshots, or chat
