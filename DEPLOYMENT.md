# Deployment

## Active Monorepo

The active push-ready codebase is `wave2_network/`.

## Arbitrum Sepolia

### Core Protocol Contracts

- `NodeAttestationRegistry`
  - `0xB54e019e9717a8Ed4746bA9d7F1A3F83cf0a35E0`
  - https://sepolia.arbiscan.io/address/0xB54e019e9717a8Ed4746bA9d7F1A3F83cf0a35E0
- `ExecutionCommitmentRegistry`
  - `0xcd45aefE9a16772528fa30B7d47958a95e83440C`
  - https://sepolia.arbiscan.io/address/0xcd45aefE9a16772528fa30B7d47958a95e83440C
- `AgentConfigRegistry`
  - `0x85aE035d6a94c006B5d0808cAdF47F5c22536996`
  - https://sepolia.arbiscan.io/address/0x85aE035d6a94c006B5d0808cAdF47F5c22536996
- `ReputationRegistry`
  - `0xdaDb4D46D231d3fe6D3754E0861c8bCD36aF0604`
  - https://sepolia.arbiscan.io/address/0xdaDb4D46D231d3fe6D3754E0861c8bCD36aF0604
- `RewardAccumulator`
  - `0xFa25Fb53eF8dAc88E4f43bB7558Cf3930Bf3e817`
  - https://sepolia.arbiscan.io/address/0xFa25Fb53eF8dAc88E4f43bB7558Cf3930Bf3e817

### Supporting Core Deployments

- `ArbiterSelectionRegistry`: `0xAaf7Dd729Cb5873975D3643bE2b89CA121143d3f`
- `MockAgentIdentityRegistry`: `0x723ef21650B66a5705eABB74c3f3a3dB1593bb62`
- `MockEscrowReleaser`: `0x6B1dC5aca048e0F5FF7fdd4831Bd721c5501b9fc`
- `PrevRandaoRandomness`: `0xA579Fb461FedA169d59481fE5A24Cb3B7beA8222`

### Blindference Demo Contracts

- `BlindferenceInputVault`
  - `0x8dD7B2A9B69C76A69d33B2DF46426Cbe657a902b`
  - https://sepolia.arbiscan.io/address/0x8dD7B2A9B69C76A69d33B2DF46426Cbe657a902b
- `MockPriceOracle`
  - `0xDe9AE4b048bF320Db6492e2AfD0516392EBA05Fc`
  - https://sepolia.arbiscan.io/address/0xDe9AE4b048bF320Db6492e2AfD0516392EBA05Fc
- `BlindferenceAttestor`
  - `0x74454F689F28EfbEF6Ef9F3F14e56ac62CA8EC49`
  - https://sepolia.arbiscan.io/address/0x74454F689F28EfbEF6Ef9F3F14e56ac62CA8EC49
- `BlindferenceUnderwriter`
  - `0xcbbdcb1b42DE4Ed52f7ceD752c65652EE317B601`
  - https://sepolia.arbiscan.io/address/0xcbbdcb1b42DE4Ed52f7ceD752c65652EE317B601
- `BlindferenceAgent`
  - `0xc9208B8aCAaD3abFc955a575719BB8F21640A6fE`
  - https://sepolia.arbiscan.io/address/0xc9208B8aCAaD3abFc955a575719BB8F21640A6fE

### Vault-Enabled Deploy Transactions

- `BlindferenceInputVault`
  - `0xc1f60f29c20f78253d45643dd5d8cd96c78615a90eadb441271396c7eb6d0408`
  - https://sepolia.arbiscan.io/tx/0xc1f60f29c20f78253d45643dd5d8cd96c78615a90eadb441271396c7eb6d0408
- `MockPriceOracle`
  - `0xb251275dd5445cb864addd50d0ef010af52fe04632321151c0bf89f29198779c`
  - https://sepolia.arbiscan.io/tx/0xb251275dd5445cb864addd50d0ef010af52fe04632321151c0bf89f29198779c
- `BlindferenceAttestor`
  - `0xe354448f72bd7953df34ecc7cec8177f2c4fb16a92a0922c99a7325482f1e028`
  - https://sepolia.arbiscan.io/tx/0xe354448f72bd7953df34ecc7cec8177f2c4fb16a92a0922c99a7325482f1e028
- `BlindferenceUnderwriter`
  - `0x351b825a8fff8a41072c1d379abb9b0bc054dc2c864dd7d61932036caed1b561`
  - https://sepolia.arbiscan.io/tx/0x351b825a8fff8a41072c1d379abb9b0bc054dc2c864dd7d61932036caed1b561
- `BlindferenceAgent`
  - `0x855084006dadf51b109e07cafe1203bf50287af2392f502a66ffa7324f90cc70`
  - https://sepolia.arbiscan.io/tx/0x855084006dadf51b109e07cafe1203bf50287af2392f502a66ffa7324f90cc70

## Smoke Tests

### Refreshed Model-ID Smoke Test

- Request ID: `44ef761893694cb186f235b210633f55`
- Task ID: `38d24a370fe191242c00d15f1e3d45c25f9e3c3eb57420d3dc61a5c069ef9803`
- Model ID: `groq:llama-3.3-70b-versatile`
- Risk score: `67`
- Result tx:
  - `0xb9b796e66f5acf0b3650f5ff86bf19d4c91b1cfc2ea218f96de8d87cd7d9cebd`
  - https://sepolia.arbiscan.io/tx/0xb9b796e66f5acf0b3650f5ff86bf19d4c91b1cfc2ea218f96de8d87cd7d9cebd

### 3-Node Quorum Smoke Test

- Request ID: `1a14cb67b3f64014bfbc0d0ca5fce728`
- Task ID: `6fab37839832a2373b0a68ff0dab9c898aeb9d314411c068b4ccfe3f2217d63b`
- Model ID: `groq:llama-3.3-70b-versatile`
- Leader: `0x61e72a024aE31ed2f0656a37b3B3172CDC364C85`
- Verifiers:
  - `0x9Cc0cBfCc4e3F45e2958F6EC0F5e70B500D0bB3E`
  - `0xdDef3Cf5A4d0A6404Bc084D74de3E2c0d6147dA5`
- Confirm count: `2`
- Reject count: `0`
- Result tx:
  - `0x513432302a783a46fd8539dd3f8a482e16d3fce5d1d5a9f305b1441f7b8669fa`
  - https://sepolia.arbiscan.io/tx/0x513432302a783a46fd8539dd3f8a482e16d3fce5d1d5a9f305b1441f7b8669fa

## Demo Notes

- The BF frontend has been fully moved into `wave2_network/packages/frontend`.
- The live CoFHE path now uses `BlindferenceInputVault` before permit creation so browser-produced ciphertext handles get issuer ACL on-chain.
- The frontend is now wired to the real ICL request lifecycle and live quorum progress.
- The demo UI includes a mock escrow release evidence step after accepted scoring so the settlement journey is recordable without a production escrow releaser.
- The correct CoFHE testnet endpoint used by the current stack is `https://testnet-cofhe.fhenix.zone`.
- Real `.env` files are intentionally not committed. Only `.env.example` files should be pushed.
