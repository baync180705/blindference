# `_reineira_stubs/` — vendored Reineira artifacts

**Delete this entire directory at chaosenet.**

## Why this exists

Blindference contracts depend on three Reineira protocol artifacts:

| Symbol | Imported as |
|---|---|
| `TestnetCoreBase` | `@reineira-os/shared/contracts/common/TestnetCoreBase.sol` |
| `FHEMeta` | `@reineira-os/shared/contracts/common/FHEMeta.sol` |
| `IEscrow` | `@reineira-os/shared/contracts/interfaces/core/IEscrow.sol` |

Reineira is private today, so these can't be `forge install`-ed from
GitHub. To keep Blindference self-contained and CI-buildable, we vendor
the artifacts here and point the `@reineira-os/shared/=` Foundry remapping
at this directory.

## Migration at chaosenet

When Reineira publishes `reineira-os/shared` publicly:

1. `forge install reineira-os/shared`
2. In [`../../foundry.toml`](../../foundry.toml), comment-flip the
   `@reineira-os/shared/=` remapping from
   `contracts/_reineira_stubs/` to `lib/shared/`.
3. **Delete this entire `contracts/_reineira_stubs/` directory.**
4. Delete [`../interfaces/TECH-DEBT.md`](../interfaces/TECH-DEBT.md).
5. Verify `forge build` and `forge test` still pass.

## Source-of-truth (today, in private repo)

```
reineira-os/platform-web3-protocol/
  packages/shared/contracts/
    common/TestnetCoreBase.sol
    common/FHEMeta.sol
    interfaces/core/IEscrow.sol     # K17 — backlog, not yet shipped
```

`IEscrow` is itself unfinished on the Reineira side (per design backlog
item K17, the abstraction over `ConfidentialEscrow`). Our local
[`contracts/interfaces/core/IEscrow.sol`](contracts/interfaces/core/IEscrow.sol)
implements only the subset Blindference calls into; the chaosenet version
will likely have more methods.
