# Blindference FHE Mocks

This package runs the official local CoFHE mock environment with `@cofhe/hardhat-plugin`.

Use it for local permit-based encryption/decryption flows while keeping Blindference protocol contracts on Anvil or Foundry.

## Install

```bash
npm install
```

## Start the mock node

```bash
npm run node
```

The Hardhat plugin deploys the CoFHE mock contracts automatically on startup.

Default RPC:

```text
http://127.0.0.1:8546
```

## Grant ACL access manually

If you need to debug local `NotAllowed` errors in the mock environment:

```bash
CT_HASH=<ciphertext-hash> OPERATOR_ADDRESS=<leader-address> REQUESTER_ADDRESS=<ciphertext-owner> npm run grant-acl
```

## Recommended local split

- Protocol contracts / Blindference demo: `anvil` on `8545`
- CoFHE mock contracts: Hardhat on `8546`
- ICL:
  - `ARBITRUM_SEPOLIA_RPC=http://127.0.0.1:8545`
  - `COFHE_RPC_URL=http://127.0.0.1:8546`
- Node runtime:
  - `BLINDFERENCE_NODE_COFHE_RPC_URL=http://127.0.0.1:8546`
