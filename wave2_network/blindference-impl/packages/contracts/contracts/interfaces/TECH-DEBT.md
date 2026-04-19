# Tech debt — Reineira dependency resolution

**Status:** Pre-chaosenet (Reineira protocol is private).
**Owner:** Resolve at chaosenet (public testnet) launch.

## Current state

Reineira is a private monorepo today, so we cannot `forge install` it.
Instead, the three Reineira artifacts Blindference depends on are
**vendored locally** in [`../_reineira_stubs/`](../_reineira_stubs/) and
the `@reineira-os/shared/=` Foundry remapping points at that directory.

| Symbol | Imported as | Local copy |
|---|---|---|
| `TestnetCoreBase` | `@reineira-os/shared/contracts/common/TestnetCoreBase.sol` | [`../_reineira_stubs/contracts/common/TestnetCoreBase.sol`](../_reineira_stubs/contracts/common/TestnetCoreBase.sol) |
| `FHEMeta` | `@reineira-os/shared/contracts/common/FHEMeta.sol` | [`../_reineira_stubs/contracts/common/FHEMeta.sol`](../_reineira_stubs/contracts/common/FHEMeta.sol) |
| `IEscrow` | `@reineira-os/shared/contracts/interfaces/core/IEscrow.sol` | [`../_reineira_stubs/contracts/interfaces/core/IEscrow.sol`](../_reineira_stubs/contracts/interfaces/core/IEscrow.sol) |

Note: `IEscrow` is itself unfinished on the Reineira side (per design
backlog item K17). The local stub declares only the subset Blindference
calls into; the chaosenet version will likely have more methods.

## Files affected

- [`../core/AgentConfigRegistry.sol`](../core/AgentConfigRegistry.sol) — `TestnetCoreBase`
- [`../core/ModelCallTicketRegistry.sol`](../core/ModelCallTicketRegistry.sol) — `TestnetCoreBase`, `FHEMeta`, `IEscrow`
- [`../core/NodeAttestationRegistry.sol`](../core/NodeAttestationRegistry.sol) — `TestnetCoreBase`
- [`../core/ExecutionCommitmentRegistry.sol`](../core/ExecutionCommitmentRegistry.sol) — `TestnetCoreBase`
- [`../core/ArbiterSelectionRegistry.sol`](../core/ArbiterSelectionRegistry.sol) — `TestnetCoreBase`
- [`../core/ReputationRegistry.sol`](../core/ReputationRegistry.sol) — `TestnetCoreBase`
- [`../core/RewardAccumulator.sol`](../core/RewardAccumulator.sol) — `TestnetCoreBase`

## Target state (chaosenet) — Foundry git deps

When Reineira's `shared` package publishes to GitHub, install it as a
Foundry git dependency and switch the remapping.

### Reference GitHub repo

- **`@reineira-os/shared`** → `github.com/reineira-os/shared`

### Migration

```bash
forge install reineira-os/shared
```

In [`../../foundry.toml`](../../foundry.toml), comment-flip the
`@reineira-os/shared/=` remapping from `contracts/_reineira_stubs/` to
`lib/shared/` (the target line is already pre-staged in the file under
the `# Target state — uncomment after:` block).

## Migration checklist (when chaosenet ships)

- [ ] Confirm `reineira-os/shared` GitHub repo is public with a stable
      v1 tag.
- [ ] Run `forge install reineira-os/shared` (pin to a specific tag).
- [ ] In [`../../foundry.toml`](../../foundry.toml): comment out the
      vendored-stub `@reineira-os/shared/=contracts/_reineira_stubs/`
      remapping; uncomment the `lib/shared/` one.
- [ ] **Delete the entire [`../_reineira_stubs/`](../_reineira_stubs/)
      directory.**
- [ ] Remove the `# === TECH DEBT (chaosenet) ===` block from
      `foundry.toml`.
- [ ] Delete this file.
- [ ] Verify `forge build` and `forge test` pass against the public
      Reineira `shared` package.
- [ ] Document the resolved version pin in the repo README.
