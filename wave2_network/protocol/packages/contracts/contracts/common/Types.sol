// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

struct PricingConfig {
    uint64 baseFee;
    uint64 maxModelSpend;
    uint64 premiumCap;
}
