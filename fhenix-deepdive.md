1. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Permits

> Create and manage EIP-712 permits for decryption authorization

Permits are EIP-712 signatures that authorize decryption of confidential data. The `issuer` field identifies who is accessing the data — the issuer must have been granted access on-chain via `FHE.allow(handle, address)`. When a permit is used, CoFHE validates it against the ACL contract to confirm that the issuer has access to the requested encrypted handle.

Each permit includes a sealing keypair. The public key is sent to CoFHE so it can re-encrypt the data for the permit holder. The private key stays client-side and is used to unseal the returned data.

## When do you need a permit?

* **`decryptForView`**: always requires a permit.
* **`decryptForTx`**: depends on the contract's ACL policy for that `ctHash`.
  * If the policy allows anyone to decrypt, you can use `.withoutPermit()`.
  * If the policy restricts decryption, you must use `.withPermit(...)`.

## Prerequisites

[Create and connect a client](/client-sdk/guides/client-setup). Permits are scoped to a **chainId + account**.

## Quick start

<Info>
  The examples below show two approaches. The `client.permits` API is the recommended approach — it automatically signs permits with the connected wallet and manages the permit store. The `PermitUtils` API is a lower-level alternative that gives you direct control over signing and storage.
</Info>

<CodeGroup>
  ```typescript client.permits (recommended) theme={null}
  await client.connect(publicClient, walletClient);

  // Returns the active self permit if one exists, otherwise creates and signs a new one.
  const permit = await client.permits.getOrCreateSelfPermit();
  ```

  ```typescript PermitUtils theme={null}
  import {
    PermitUtils,
    setPermit,
    setActivePermitHash,
  } from '@cofhe/sdk/permits';

  const permit = await PermitUtils.createSelfAndSign(
    { issuer: walletClient.account.address },
    publicClient,
    walletClient
  );

  // Manually store and activate the permit
  const chainId = await publicClient.getChainId();
  const account = walletClient.account.address;
  setPermit(chainId, account, permit);
  setActivePermitHash(chainId, account, permit.hash);
  ```
</CodeGroup>

After this, the active permit is picked up automatically:

* `decryptForView(...).execute()` uses the active permit.
* `decryptForTx(...).withPermit().execute()` uses the active permit.

## Permit types

| Type        | Who signs                             | Use case                                                  |
| ----------- | ------------------------------------- | --------------------------------------------------------- |
| `self`      | issuer only                           | Decrypt your own data (most common)                       |
| `sharing`   | issuer only                           | A shareable "offer" created by the issuer for a recipient |
| `recipient` | recipient (includes issuer signature) | The imported permit after the recipient signs it          |

<Note>
  * Permit `expiration` is a unix timestamp in **seconds**. The default is **7 days from creation**.
  * When a permit is created via `client.permits.*`, it is automatically stored and set as the active permit.
</Note>

## Creating a self permit

A self permit lets you decrypt data that was allowed to your address.

### createSelf

<CodeGroup>
  ```typescript client.permits theme={null}
  await client.connect(publicClient, walletClient);

  const permit = await client.permits.createSelf({
    issuer: walletClient.account.address,
    name: 'My self permit',
  });

  permit.type; // 'self'
  permit.hash; // deterministic hash
  ```

  ```typescript PermitUtils theme={null}
  import { PermitUtils } from '@cofhe/sdk/permits';

  const permit = await PermitUtils.createSelfAndSign(
    {
      issuer: walletClient.account.address,
      name: 'My self permit',
    },
    publicClient,
    walletClient
  );

  permit.type; // 'self'
  permit.hash; // deterministic hash
  ```
</CodeGroup>

### getOrCreateSelfPermit

Returns the active self permit if one exists. Otherwise creates and signs a new one. This is the recommended approach for most applications.

```typescript theme={null}
await client.connect(publicClient, walletClient);

const permit = await client.permits.getOrCreateSelfPermit();
permit.type; // 'self'
```

## Sharing permits

Sharing permits let an issuer delegate their ACL access to a recipient. The recipient can then decrypt the issuer's data without needing their own `FHE.allow`.

<Steps>
  <Step title="Issuer creates a sharing permit">
    The issuer creates a sharing permit specifying the recipient's address.

    <CodeGroup>
      ```typescript client.permits theme={null}
      await client.connect(publicClient, walletClient);

      const sharingPermit = await client.permits.createSharing({
        issuer: walletClient.account.address,
        recipient,
        name: 'Share with recipient',
      });
      ```

      ```typescript PermitUtils theme={null}
      import { PermitUtils } from '@cofhe/sdk/permits';

      const sharingPermit = await PermitUtils.createSharingAndSign(
        {
          issuer: walletClient.account.address,
          recipient,
          name: 'Share with recipient',
        },
        publicClient,
        walletClient
      );
      ```
    </CodeGroup>
  </Step>

  <Step title="Issuer exports the permit">
    Export the permit as a JSON blob and share it with the recipient.

    ```typescript theme={null}
    import { PermitUtils } from '@cofhe/sdk/permits';

    const exported = PermitUtils.export(sharingPermit);
    ```

    <Info>
      The exported JSON does not contain any sensitive data and can be shared via any channel.
    </Info>

    <Warning>
      Do not share `serialize(permit)` output — serialization is meant for local persistence and includes the sealing private key.
    </Warning>
  </Step>

  <Step title="Recipient imports and signs">
    The recipient imports the exported JSON and signs it with their wallet. On import, a new sealing key is generated for the recipient.

    <CodeGroup>
      ```typescript client.permits theme={null}
      await client.connect(publicClient, walletClient);

      const recipientPermit = await client.permits.importShared(exported);

      recipientPermit.type; // 'recipient'
      recipientPermit.hash;
      ```

      ```typescript PermitUtils theme={null}
      import {
        PermitUtils,
        setPermit,
        setActivePermitHash,
      } from '@cofhe/sdk/permits';

      const recipientPermit = await PermitUtils.importSharedAndSign(
        exported,
        publicClient,
        walletClient
      );

      const chainId = await publicClient.getChainId();
      const account = walletClient.account.address;
      setPermit(chainId, account, recipientPermit);
      setActivePermitHash(chainId, account, recipientPermit.hash);
      ```
    </CodeGroup>
  </Step>
</Steps>

## Active permit management

The SDK tracks all stored permits and an **active permit hash** per `chainId + account`. Creating or importing a permit via `client.permits.*` automatically stores it and selects it as active.

### List stored permits

```typescript theme={null}
const permits = client.permits.getPermits();
Object.keys(permits); // permit hashes
```

### Read / select the active permit

```typescript theme={null}
const active = client.permits.getActivePermit();
active?.hash;

client.permits.selectActivePermit(somePermitHash);
```

### Removing permits

```typescript theme={null}
client.permits.removePermit(permitHash);
client.permits.removeActivePermit();
```

## Persistence and security

* The SDK persists permits in a store keyed by `chainId + account`.
* In web environments, this store uses `localStorage` under the key `cofhesdk-permits`.
* A stored permit includes the **sealing private key**. Treat it like a secret.
  * Never share serialized permits with other users.
  * To share access, use `PermitUtils.export(...)` which strips sensitive fields.

2. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# TaskManager

> On-chain entry point for CoFHE integration that initiates FHE operations, generates unique handles, and verifies decrypt result signatures

| Aspect               | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Type**             | Contract deployed on the destination blockchain                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Function**         | Acts as the on-chain entry point for CoFHE integration                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Responsibilities** | • Initiates FHE operations by serving as the on-chain entry point. The dApp contract calls the FHE.sol library which triggers the TaskManager contract to submit a new encrypted computation task. <br />• Generates unique handles that act as references to the results of FHE operations. These results are computed asynchronously off-chain. <br />• Emits structured events containing the unique handle of the ciphertext, operation type, and other required metadata. <br />• Verifies ECDSA signatures on client-published decrypt results and stores them on-chain. |
| **Deployment**       | A separate Task Manager Contract is deployed for each supported destination chain, enabling chain-specific integrations                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

## Decrypt Result Signature Verification

The TaskManager supports **permissionless publishing of decrypt results**. Anyone holding a valid ECDSA signature from the Threshold Network's Dispatcher can publish a decrypt result on-chain. The TaskManager verifies the signature before storing the result.

### Key State

| Variable              | Description                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------- |
| `decryptResultSigner` | Address of the authorized Threshold Network signer. Set to `address(0)` to skip verification (debug mode). |

### Functions

| Function                                                         | Description                                                                       |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `publishDecryptResult(ctHash, result, signature)`                | Verify signature and store the decrypt result on-chain. Emits `DecryptionResult`. |
| `publishDecryptResultBatch(ctHashes[], results[], signatures[])` | Batch publish multiple results in one transaction for gas efficiency.             |
| `verifyDecryptResult(ctHash, result, signature)`                 | Verify a signature without publishing (view). Reverts on failure.                 |
| `verifyDecryptResultSafe(ctHash, result, signature)`             | Verify a signature without publishing (view). Returns `false` on failure.         |
| `setDecryptResultSigner(address)`                                | Admin-only. Set the authorized signer address.                                    |

### Signature Message Format

The signed message is a fixed **76-byte** buffer:

| Field      | Size     | Encoding                                         |
| ---------- | -------- | ------------------------------------------------ |
| `result`   | 32 bytes | uint256, big-endian, left-padded with zeros      |
| `enc_type` | 4 bytes  | i32, big-endian (extracted from ctHash metadata) |
| `chain_id` | 8 bytes  | u64, big-endian (from `block.chainid`)           |
| `ct_hash`  | 32 bytes | uint256, big-endian                              |

The message is hashed with `keccak256` and verified using OpenZeppelin's `ECDSA.tryRecover`. The `enc_type` and `chain_id` are derived on-chain, binding each signature to a specific ciphertext type and chain.

3. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# TaskManager

> On-chain entry point for CoFHE integration that initiates FHE operations, generates unique handles, and verifies decrypt result signatures

| Aspect               | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Type**             | Contract deployed on the destination blockchain                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Function**         | Acts as the on-chain entry point for CoFHE integration                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Responsibilities** | • Initiates FHE operations by serving as the on-chain entry point. The dApp contract calls the FHE.sol library which triggers the TaskManager contract to submit a new encrypted computation task. <br />• Generates unique handles that act as references to the results of FHE operations. These results are computed asynchronously off-chain. <br />• Emits structured events containing the unique handle of the ciphertext, operation type, and other required metadata. <br />• Verifies ECDSA signatures on client-published decrypt results and stores them on-chain. |
| **Deployment**       | A separate Task Manager Contract is deployed for each supported destination chain, enabling chain-specific integrations                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

## Decrypt Result Signature Verification

The TaskManager supports **permissionless publishing of decrypt results**. Anyone holding a valid ECDSA signature from the Threshold Network's Dispatcher can publish a decrypt result on-chain. The TaskManager verifies the signature before storing the result.

### Key State

| Variable              | Description                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------- |
| `decryptResultSigner` | Address of the authorized Threshold Network signer. Set to `address(0)` to skip verification (debug mode). |

### Functions

| Function                                                         | Description                                                                       |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `publishDecryptResult(ctHash, result, signature)`                | Verify signature and store the decrypt result on-chain. Emits `DecryptionResult`. |
| `publishDecryptResultBatch(ctHashes[], results[], signatures[])` | Batch publish multiple results in one transaction for gas efficiency.             |
| `verifyDecryptResult(ctHash, result, signature)`                 | Verify a signature without publishing (view). Reverts on failure.                 |
| `verifyDecryptResultSafe(ctHash, result, signature)`             | Verify a signature without publishing (view). Returns `false` on failure.         |
| `setDecryptResultSigner(address)`                                | Admin-only. Set the authorized signer address.                                    |

### Signature Message Format

The signed message is a fixed **76-byte** buffer:

| Field      | Size     | Encoding                                         |
| ---------- | -------- | ------------------------------------------------ |
| `result`   | 32 bytes | uint256, big-endian, left-padded with zeros      |
| `enc_type` | 4 bytes  | i32, big-endian (extracted from ctHash metadata) |
| `chain_id` | 8 bytes  | u64, big-endian (from `block.chainid`)           |
| `ct_hash`  | 32 bytes | uint256, big-endian                              |

The message is hashed with `keccak256` and verified using OpenZeppelin's `ECDSA.tryRecover`. The `enc_type` and `chain_id` are derived on-chain, binding each signature to a specific ciphertext type and chain.

4. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Slim Listener

> Off-chain service that monitors blockchain events and forwards FHE operation requests to the computation layer

| Aspect               | Description                                                                                                                                                                                                                              |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Off-chain event monitoring service                                                                                                                                                                                                       |
| **Function**         | Listens to blockchain events and forwards FHE operation requests to the fheOS server                                                                                                                                                     |
| **Responsibilities** | • Monitors events emitted by the Task Manager contract on the destination chain<br />• Processes incoming requests and forwards them to the fheOS server<br />• Ensures reliable delivery of operation requests to the computation layer |

The Slim Listener acts as the bridge between on-chain events and the off-chain computation layer, ensuring that all FHE operation requests are captured and forwarded for processing.

5. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Slim Listener

> Off-chain service that monitors blockchain events and forwards FHE operation requests to the computation layer

| Aspect               | Description                                                                                                                                                                                                                              |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Off-chain event monitoring service                                                                                                                                                                                                       |
| **Function**         | Listens to blockchain events and forwards FHE operation requests to the fheOS server                                                                                                                                                     |
| **Responsibilities** | • Monitors events emitted by the Task Manager contract on the destination chain<br />• Processes incoming requests and forwards them to the fheOS server<br />• Ensures reliable delivery of operation requests to the computation layer |

The Slim Listener acts as the bridge between on-chain events and the off-chain computation layer, ensuring that all FHE operation requests are captured and forwarded for processing.

6. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Plaintexts Storage

> Internal smart contract that manages storage and retrieval of plaintext values in the host chain with caching mechanisms

| Aspect               | Description                                                                                                                                                                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Internal Smart Contract                                                                                                                                                                                                                       |
| **Function**         | Storage and management of plaintext values in the host chain                                                                                                                                                                                  |
| **Responsibilities** | • Manages the storage and retrieval of plaintext values in the system <br /> • Provides caching mechanism for plaintext values to improve retrieval performance <br /> • Ensures secure handling of decrypted data within the CoFHE ecosystem |

7. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

8. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

9. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

10. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

11. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

12. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

13. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

14. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# CTRegistry

> Registry contract that manages the mapping between temporary ciphertext hashes and their actual hash values, ensuring secure lookup and verification

| Aspect               | Description                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**             | Registry Contract                                                                                                                                                                                                                                                |
| **Function**         | Manages the mapping between temporary ciphertext hashes and their actual hash values                                                                                                                                                                             |
| **Responsibilities** | • Maintains a consistent record of ciphertext identifiers throughout the CoFHE lifecycle<br />• Enables secure lookup of final ciphertexts using their temporary handles<br />• Restricts read/write access to ensure integrity and prevent unauthorized updates |

The CTRegistry acts as a source of truth for encrypted data identifiers, mapping temporary hashes to their final computed values. This ensures results from off-chain computation can be securely resolved and verified by their originating requests.

16. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Future Plans

> Roadmap for CoFHE decentralization, upcoming features, and planned improvements

Future Plans

## Road to Decentralization

Integrating FHE into a blockchain-runtime is a hard and complex task. Our engineering philosophy is *Ship Fast*, and we believe that to build the best possible product we need to meet real users early. Similar to the approach described in [Vitalik's "training wheels" post](https://ethereum-magicians.org/t/proposed-milestones-for-rollups-taking-off-training-wheels/11571) (in the context of rollups), we too are relying on "training wheels" releasing CoFHE to achieve this goal.

Outlined here is a non-exhaustive list of trust-points, centralized components and compromises made to ship CoFHE to users as fast as possible, along with how we plan to address them in the future. This list will be updated as things progress.

| Component              | Compromise                                                   | Plan to solve                                                                      | Timeline | Status |
| ---------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------- | ------ |
| Threshold Network (TN) | All parties are run by Fhenix                                | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Use of a Trusted Dealer for keys and random data generation  | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Parties trust the Coordinator                                | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | TN trusts CoFHE (tx-flow decryptions)                        | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Parties trust a Trusted Dealer                               | 1. Run TD in a TEE<br />2. Public ceremony for share creation<br />3. Eliminate TD | N/A      | ❌      |
| Threshold Network (TN) | Parties are not using unique random data within the protocol | Pull random data from the TD                                                       | N/A      | ❌      |
| Threshold Network (TN) | SealOutput reencryption performed in a centralized manner    | N/A                                                                                | N/A      | ❌      |
| ZK-Verifier (ZKV)      | CoFHE trusts ZK-Verifier                                     | Run ZKV in a TEE                                                                   | N/A      | ❌      |
| CoFHE                  | Trust in CoFHE to perform correct FHE computations           | External verification using AVS                                                    | N/A      | ❌      |
| CoFHE                  | User inputs stored in a centralized manner                   | Use a decentralized DA                                                             | N/A      | ❌      |
| All                    | Codebase is unaudited                                        | Perform a security audit                                                           | N/A      | ❌      |
| All                    | Codebase is not fully open-source                            | Open-source codebase                                                               | N/A      | ❌      |

## Upcoming Features

In the spirit of transparency, here we describe the general feature-roadmap planned for CoFHE. This list will be updated as things progress.

| Feature                        | Type                | Description                                                                      | Timeline | Status |
| ------------------------------ | ------------------- | -------------------------------------------------------------------------------- | -------- | ------ |
| Integration SDK                | DevX                | SDK to easily integrate CoFHE-specific components into dApps                     | N/A      | ❌      |
| Additional external devtools   | DevX                | Remix, Alchemy SDK and more                                                      | N/A      | ❌      |
| RNG                            | DevX                | Ability to generate secure randomness in contracts                               | N/A      | ❌      |
| Alternative runtimes           | DevX                | Support for additional runtimes other than EVM                                   | N/A      | ❌      |
| FHE ops in view functions      | DevX                | Ability to execute FHE operations in view functions in contracts                 | N/A      | ❌      |
| GPU support                    | UX                  | Run FHE operations on a GPU backend, improving performance and overall latency   | N/A      | ❌      |
| FPGA support                   | UX                  | Run FHE operations on an FPGA backend, improving performance and overall latency | N/A      | ❌      |
| T-out-of-N MPC protocol        | Robustness          | Improve robustness of the TN by not requiring all parties to be online           | N/A      | ❌      |
| Support additional host-chains | DevX/UX             | N/A                                                                              | N/A      | ❌      |
| Key shares rotation            | Robustness/Security | Ability to rotate the party shares in the TN                                     | N/A      | ❌      |
| Key Rotation                   | Robustness/Security | Ability to rotate the key for the entire protocol                                | N/A      | ❌      |

17. > ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Future Plans

> Roadmap for CoFHE decentralization, upcoming features, and planned improvements

Future Plans

## Road to Decentralization

Integrating FHE into a blockchain-runtime is a hard and complex task. Our engineering philosophy is *Ship Fast*, and we believe that to build the best possible product we need to meet real users early. Similar to the approach described in [Vitalik's "training wheels" post](https://ethereum-magicians.org/t/proposed-milestones-for-rollups-taking-off-training-wheels/11571) (in the context of rollups), we too are relying on "training wheels" releasing CoFHE to achieve this goal.

Outlined here is a non-exhaustive list of trust-points, centralized components and compromises made to ship CoFHE to users as fast as possible, along with how we plan to address them in the future. This list will be updated as things progress.

| Component              | Compromise                                                   | Plan to solve                                                                      | Timeline | Status |
| ---------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------- | ------ |
| Threshold Network (TN) | All parties are run by Fhenix                                | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Use of a Trusted Dealer for keys and random data generation  | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Parties trust the Coordinator                                | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | TN trusts CoFHE (tx-flow decryptions)                        | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Parties trust a Trusted Dealer                               | 1. Run TD in a TEE<br />2. Public ceremony for share creation<br />3. Eliminate TD | N/A      | ❌      |
| Threshold Network (TN) | Parties are not using unique random data within the protocol | Pull random data from the TD                                                       | N/A      | ❌      |
| Threshold Network (TN) | SealOutput reencryption performed in a centralized manner    | N/A                                                                                | N/A      | ❌      |
| ZK-Verifier (ZKV)      | CoFHE trusts ZK-Verifier                                     | Run ZKV in a TEE                                                                   | N/A      | ❌      |
| CoFHE                  | Trust in CoFHE to perform correct FHE computations           | External verification using AVS                                                    | N/A      | ❌      |
| CoFHE                  | User inputs stored in a centralized manner                   | Use a decentralized DA                                                             | N/A      | ❌      |
| All                    | Codebase is unaudited                                        | Perform a security audit                                                           | N/A      | ❌      |
| All                    | Codebase is not fully open-source                            | Open-source codebase                                                               | N/A      | ❌      |

## Upcoming Features

In the spirit of transparency, here we describe the general feature-roadmap planned for CoFHE. This list will be updated as things progress.

| Feature                        | Type                | Description                                                                      | Timeline | Status |
| ------------------------------ | ------------------- | -------------------------------------------------------------------------------- | -------- | ------ |
| Integration SDK                | DevX                | SDK to easily integrate CoFHE-specific components into dApps                     | N/A      | ❌      |
| Additional external devtools   | DevX                | Remix, Alchemy SDK and more                                                      | N/A      | ❌      |
| RNG                            | DevX                | Ability to generate secure randomness in contracts                               | N/A      | ❌      |
| Alternative runtimes           | DevX                | Support for additional runtimes other than EVM                                   | N/A      | ❌      |
| FHE ops in view functions      | DevX                | Ability to execute FHE operations in view functions in contracts                 | N/A      | ❌      |
| GPU support                    | UX                  | Run FHE operations on a GPU backend, improving performance and overall latency   | N/A      | ❌      |
| FPGA support                   | UX                  | Run FHE operations on an FPGA backend, improving performance and overall latency | N/A      | ❌      |
| T-out-of-N MPC protocol        | Robustness          | Improve robustness of the TN by not requiring all parties to be online           | N/A      | ❌      |
| Support additional host-chains | DevX/UX             | N/A                                                                              | N/A      | ❌      |
| Key shares rotation            | Robustness/Security | Ability to rotate the party shares in the TN                                     | N/A      | ❌      |
| Key Rotation                   | Robustness/Security | Ability to rotate the key for the entire protocol                                | N/A      | ❌      |
> ## Documentation Index
> Fetch the complete documentation index at: https://cofhe-docs.fhenix.zone/llms.txt
> Use this file to discover all available pages before exploring further.

# Future Plans

> Roadmap for CoFHE decentralization, upcoming features, and planned improvements

Future Plans

## Road to Decentralization

Integrating FHE into a blockchain-runtime is a hard and complex task. Our engineering philosophy is *Ship Fast*, and we believe that to build the best possible product we need to meet real users early. Similar to the approach described in [Vitalik's "training wheels" post](https://ethereum-magicians.org/t/proposed-milestones-for-rollups-taking-off-training-wheels/11571) (in the context of rollups), we too are relying on "training wheels" releasing CoFHE to achieve this goal.

Outlined here is a non-exhaustive list of trust-points, centralized components and compromises made to ship CoFHE to users as fast as possible, along with how we plan to address them in the future. This list will be updated as things progress.

| Component              | Compromise                                                   | Plan to solve                                                                      | Timeline | Status |
| ---------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------- | ------ |
| Threshold Network (TN) | All parties are run by Fhenix                                | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Use of a Trusted Dealer for keys and random data generation  | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Parties trust the Coordinator                                | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | TN trusts CoFHE (tx-flow decryptions)                        | N/A                                                                                | N/A      | ❌      |
| Threshold Network (TN) | Parties trust a Trusted Dealer                               | 1. Run TD in a TEE<br />2. Public ceremony for share creation<br />3. Eliminate TD | N/A      | ❌      |
| Threshold Network (TN) | Parties are not using unique random data within the protocol | Pull random data from the TD                                                       | N/A      | ❌      |
| Threshold Network (TN) | SealOutput reencryption performed in a centralized manner    | N/A                                                                                | N/A      | ❌      |
| ZK-Verifier (ZKV)      | CoFHE trusts ZK-Verifier                                     | Run ZKV in a TEE                                                                   | N/A      | ❌      |
| CoFHE                  | Trust in CoFHE to perform correct FHE computations           | External verification using AVS                                                    | N/A      | ❌      |
| CoFHE                  | User inputs stored in a centralized manner                   | Use a decentralized DA                                                             | N/A      | ❌      |
| All                    | Codebase is unaudited                                        | Perform a security audit                                                           | N/A      | ❌      |
| All                    | Codebase is not fully open-source                            | Open-source codebase                                                               | N/A      | ❌      |

## Upcoming Features

In the spirit of transparency, here we describe the general feature-roadmap planned for CoFHE. This list will be updated as things progress.

| Feature                        | Type                | Description                                                                      | Timeline | Status |
| ------------------------------ | ------------------- | -------------------------------------------------------------------------------- | -------- | ------ |
| Integration SDK                | DevX                | SDK to easily integrate CoFHE-specific components into dApps                     | N/A      | ❌      |
| Additional external devtools   | DevX                | Remix, Alchemy SDK and more                                                      | N/A      | ❌      |
| RNG                            | DevX                | Ability to generate secure randomness in contracts                               | N/A      | ❌      |
| Alternative runtimes           | DevX                | Support for additional runtimes other than EVM                                   | N/A      | ❌      |
| FHE ops in view functions      | DevX                | Ability to execute FHE operations in view functions in contracts                 | N/A      | ❌      |
| GPU support                    | UX                  | Run FHE operations on a GPU backend, improving performance and overall latency   | N/A      | ❌      |
| FPGA support                   | UX                  | Run FHE operations on an FPGA backend, improving performance and overall latency | N/A      | ❌      |
| T-out-of-N MPC protocol        | Robustness          | Improve robustness of the TN by not requiring all parties to be online           | N/A      | ❌      |
| Support additional host-chains | DevX/UX             | N/A                                                                              | N/A      | ❌      |
| Key shares rotation            | Robustness/Security | Ability to rotate the party shares in the TN                                     | N/A      | ❌      |
| Key Rotation                   | Robustness/Security | Ability to rotate the key for the entire protocol                                | N/A      | ❌      |
