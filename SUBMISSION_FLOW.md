# Wave 1 Submission Flow

## Demo goal

Show that Blindference supports two clear actors in a confidential AI marketplace:

- `Data Source`
- `AI Lab`

while keeping:

- wallet identity cryptographic
- AI Lab authority on-chain
- encrypted compute in the Fhenix flow
- MongoDB limited to metadata/orchestration

## Suggested demo path

### 1. Connect as AI Lab

1. Connect MetaMask with wallet A.
2. Choose `AI Lab`.
3. Sign the Blindference authentication message.
4. Open `Profile` and show the wallet-bound app metadata.
5. Open `Lab` and activate the AI Lab on-chain.
6. Register the encrypted model.

Call out:

- wallet-signed authentication
- on-chain AI Lab activation through `ModelRegistry`
- encrypted model parameters registered with CoFHE/Fhenix

### 2. Switch to Data Source

1. Switch MetaMask to wallet B.
2. Choose `Data Source`.
3. Sign the Blindference authentication message.
4. Open `Profile` and show the wallet-bound app metadata.
5. Open `Source` and upload an encrypted dataset artifact.
6. Open `Market` and choose a model.
7. Open `Portal` and submit blind inference.
8. Decrypt the result.

Call out:

- Data Source plaintext stays local until encrypted
- Mongo only stores manifests / orchestration metadata
- on-chain contracts handle pricing and encrypted compute
- only the requesting wallet can decrypt the result

## What to say clearly

- Wallet address is the user identity.
- Backend auth is signature-based, not address-by-POST.
- AI Lab identity is canonical on-chain.
- MongoDB is not the protocol authority.
- PPML is the off-chain encrypted ML engine.
- Blindference is the product, wallet, contract, and orchestration layer.

## Known boundaries

- Profile metadata is off-chain.
- Dataset manifests and submission tracking are off-chain.
- AI Lab authority and encrypted inference are on-chain.
- Direct PPML export ingestion can be deepened in later milestones.
