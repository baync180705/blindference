# Blindference Wave 2 Deployment

## Arbitrum Sepolia

### Core Protocol Contracts

- `NodeAttestationRegistry`: `0xB54e019e9717a8Ed4746bA9d7F1A3F83cf0a35E0`
  - https://sepolia.arbiscan.io/address/0xB54e019e9717a8Ed4746bA9d7F1A3F83cf0a35E0
- `ExecutionCommitmentRegistry`: `0xcd45aefE9a16772528fa30B7d47958a95e83440C`
  - https://sepolia.arbiscan.io/address/0xcd45aefE9a16772528fa30B7d47958a95e83440C
- `AgentConfigRegistry`: `0x85aE035d6a94c006B5d0808cAdF47F5c22536996`
  - https://sepolia.arbiscan.io/address/0x85aE035d6a94c006B5d0808cAdF47F5c22536996
- `ReputationRegistry`: `0xdaDb4D46D231d3fe6D3754E0861c8bCD36aF0604`
  - https://sepolia.arbiscan.io/address/0xdaDb4D46D231d3fe6D3754E0861c8bCD36aF0604
- `RewardAccumulator`: `0xFa25Fb53eF8dAc88E4f43bB7558Cf3930Bf3e817`
  - https://sepolia.arbiscan.io/address/0xFa25Fb53eF8dAc88E4f43bB7558Cf3930Bf3e817

### Supporting Core Deployments

- `ArbiterSelectionRegistry`: `0xAaf7Dd729Cb5873975D3643bE2b89CA121143d3f`
- `MockAgentIdentityRegistry`: `0x723ef21650B66a5705eABB74c3f3a3dB1593bb62`
- `MockEscrowReleaser`: `0x6B1dC5aca048e0F5FF7fdd4831Bd721c5501b9fc`
- `PrevRandaoRandomness`: `0xA579Fb461FedA169d59481fE5A24Cb3B7beA8222`

### Blindference Demo Contracts

- `MockPriceOracle`: `0xfA0783F59Ac0BE6084382D6A0Fc60ffEA05E2231`
  - https://sepolia.arbiscan.io/address/0xfA0783F59Ac0BE6084382D6A0Fc60ffEA05E2231
- `BlindferenceAttestor`: `0x987A967975f8784fF72D7556d52133cb58B0f5D9`
  - https://sepolia.arbiscan.io/address/0x987A967975f8784fF72D7556d52133cb58B0f5D9
- `BlindferenceUnderwriter`: `0x3Df515fA69360F939cffAD88f270116aB93674dE`
  - https://sepolia.arbiscan.io/address/0x3Df515fA69360F939cffAD88f270116aB93674dE
- `BlindferenceAgent`: `0xb794F662d62739e81eB2F353F04bBC2A1E6A2bde`
  - https://sepolia.arbiscan.io/address/0xb794F662d62739e81eB2F353F04bBC2A1E6A2bde

## Oracle Seed Transactions

- `ETH/USDC` seed tx: `0xa29204928fcf13431a3a65ca36e50be111f8af8388aa619eaaa419311610a871`
  - https://sepolia.arbiscan.io/tx/0xa29204928fcf13431a3a65ca36e50be111f8af8388aa619eaaa419311610a871
- `BTC/USDC` seed tx: `0xec05d5c23de8ed90c061631cc429f52d4f809fd74b2c195d1e7f5021f0728fe7`
  - https://sepolia.arbiscan.io/tx/0xec05d5c23de8ed90c061631cc429f52d4f809fd74b2c195d1e7f5021f0728fe7

## Demo Deployment Transactions

- `MockPriceOracle` deploy: `0x22110b58a2e7d5ff54860993379124f0858e230fca9905bb54b783d8d10d33af`
- `BlindferenceAttestor` implementation deploy: `0x1ee55ff6b9165ab5f2b2e50eea175330b1e12113da5991784dc3b8001dc11502`
- `BlindferenceAttestor` proxy deploy: `0xd650ce7924a10d1f21e57daf67ae82c0f60477089ab61209c5b80c0d44902c58`
- `BlindferenceUnderwriter` implementation deploy: `0x33fe8d82d5f05c14c6cd03c5a53bb825d661c5120790233ff13e6776672bc308`
- `BlindferenceUnderwriter` proxy deploy: `0x5c7183afb536c5a987163c4a8e9af57ebb35c3c1418c597bd889244f328608a9`
- `BlindferenceAgent` deploy: `0xc817a04c650f62378ba17d1ef1c2ba6373078937511d691407901609ec581d2c`
- `AgentConfigRegistry.configure` tx: `0x771624ed5b52ea8af4f3dc2074242e64afc3d31df8badbb468d53e7af9f10f4e`

## Verification Notes

- All core protocol contracts listed above are deployed and verified on Arbitrum Sepolia.
- The Blindference demo deployment is also verified on Arbitrum Sepolia.
- The initial core deploy hit the deprecated Arbiscan V1 verifier endpoint; verification was resumed successfully with Foundry's current verifier flow.

## Sepolia Smoke Test

- Request ID: `85866ae2117e43c8b251b44721f48276`
- Task ID: `0xafcedb4e9872f87f2f354b5b8636dc058cc7be66ac45f71e697443b5a447f2b5`
- Result tx hash: `0x5930e0c1d046c4cfa15ed7e54f6e1de508b3461d40bd3435241d709138a4388b`
  - https://sepolia.arbiscan.io/tx/0x5930e0c1d046c4cfa15ed7e54f6e1de508b3461d40bd3435241d709138a4388b
- Quorum:
  - Leader: `0x7F9B413Da50e72415b16Eb9df6e5E59774a338dc`
  - Verifier: `0xdDef3Cf5A4d0A6404Bc084D74de3E2c0d6147dA5`
- Bootstrap attestation txs:
  - `0xbd3076b9d1112f82090a4010f4a693bda8d7730b97bbbf63d5ba139e353704b8`
  - `0xb0cad3189b80d1df245e2ee5de93d857358e9b4b5b726c603b7c7d5d253a71bd`

## Notes

- The live smoke test succeeded with a temporary 2-operator setup:
  - one funded operator from `DEMO_OPERATOR_PRIVATE_KEYS`
  - the funded deployer wallet reused as the second operator and ICL dispatcher
- `packages/icl/chain/web3_client.py` was updated to submit EIP-1559 style transactions so Arbitrum Sepolia accepts the ICL's on-chain writes.
- `packages/icl/.env` now points at the working Sepolia RPC URL from `packages/contracts/.env`.
- The configured `ICL_SERVICE_PRIVATE_KEY` in `packages/icl/.env` still needs Sepolia ETH if you want to run the same flow without temporary runtime overrides.
