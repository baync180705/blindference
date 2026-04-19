// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

// =====================================================================
// === REMOVE AT CHAOSENET — vendored Reineira artifact ================
// =====================================================================
// Local stub of @reineira-os/shared/contracts/interfaces/core/IEscrow.sol
// Source-of-truth: reineira-os/shared (private until chaosenet).
//
// Reineira backlog item K17 — `IEscrow` is the abstraction over
// `ConfidentialEscrow` that lets escrow funding sources (FHERC20, x402,
// fiat, attestation) plug in interchangeably. The Reineira-side spec is
// not yet finalized; this stub declares only the subset Blindference
// calls into. The chaosenet version will likely have additional methods
// (e.g., create, redeem, status).
//
// See contracts/_reineira_stubs/REMOVE-AT-CHAOSENET.md for migration.
// =====================================================================

import {euint64} from "@fhenixprotocol/cofhe-contracts/FHE.sol";

interface IEscrow {
    /// @notice Returns true if `escrowId` has at least `amount` budget for `claimant`.
    /// @dev Used by Blindference's `ModelCallTicketRegistry.issue(...)` to gate ticket
    ///      issuance against the agent's available escrow budget.
    function hasBudget(uint256 escrowId, address claimant, euint64 amount)
        external view returns (bool);
}
