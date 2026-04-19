// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2026 Reineira Labs Ltd. All rights reserved.
pragma solidity ^0.8.24;

import {TestnetCoreBase} from "@reineira-os/shared/contracts/common/TestnetCoreBase.sol";
import {IArbiterSelectionRegistry} from "../interfaces/core/IArbiterSelectionRegistry.sol";
import {IExecutionCommitmentRegistry as IECR} from "../interfaces/core/IExecutionCommitmentRegistry.sol";
import {IRandomnessProvider} from "../interfaces/core/IRandomnessProvider.sol";

contract ArbiterSelectionRegistry is TestnetCoreBase, IArbiterSelectionRegistry {
    /// @custom:storage-location erc7201:blindference.ArbiterSelectionRegistry
    struct Layout {
        IECR executionRegistry;
        IRandomnessProvider randomness;
        uint256 minArbiterStake;
        uint64 commitWindow;
        uint64 revealWindow;
        uint64 cooldownBlocks;

        address[] pool;
        mapping(address arbiter => uint256) poolIndex;
        mapping(address arbiter => uint256) stake;

        mapping(uint256 invocationId => Arbitration) arbitrations;
        mapping(uint256 invocationId => mapping(address arbiter => bool)) selected;
        mapping(uint256 invocationId => mapping(address arbiter => bytes32)) commits;
        mapping(uint256 invocationId => mapping(address arbiter => bytes32)) reveals;
        mapping(uint256 invocationId => mapping(address arbiter => bool)) committed;
        mapping(uint256 invocationId => mapping(address arbiter => bool)) revealed;

        mapping(address arbiter => mapping(address subject => uint256)) lastArbitratedAt;
    }

    bytes32 private constant _LAYOUT_SLOT = 0xa9b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a000;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address trustedForwarder_) TestnetCoreBase(trustedForwarder_) {
        _disableInitializers();
    }

    function initialize(
        address owner_,
        address executionRegistry_,
        address randomness_,
        uint256 minArbiterStake_,
        uint64 commitWindow_,
        uint64 revealWindow_,
        uint64 cooldownBlocks_
    ) external initializer {
        require(executionRegistry_ != address(0) && randomness_ != address(0), "ZeroAddress");
        require(commitWindow_ > 0 && revealWindow_ > 0, "ZeroWindow");
        __TestnetCoreBase_init(owner_);
        Layout storage l = _layout();
        l.executionRegistry = IECR(executionRegistry_);
        l.randomness = IRandomnessProvider(randomness_);
        l.minArbiterStake = minArbiterStake_;
        l.commitWindow = commitWindow_;
        l.revealWindow = revealWindow_;
        l.cooldownBlocks = cooldownBlocks_;
    }

    function setRandomness(address randomness_) external onlyOwner {
        require(randomness_ != address(0), "ZeroAddress");
        _layout().randomness = IRandomnessProvider(randomness_);
    }

    function registerArbiter() external payable nonReentrant {
        Layout storage l = _layout();
        if (msg.value < l.minArbiterStake) {
            revert InsufficientStake();
        }

        address arbiter = _msgSender();
        if (l.stake[arbiter] != 0) {
            revert AlreadyRegistered();
        }

        l.stake[arbiter] = msg.value;
        l.poolIndex[arbiter] = l.pool.length + 1;
        l.pool.push(arbiter);

        emit ArbiterRegistered(arbiter, msg.value);
    }

    function unregisterArbiter() external nonReentrant {
        Layout storage l = _layout();
        address arbiter = _msgSender();
        uint256 staked = l.stake[arbiter];
        if (staked == 0) {
            revert NotRegistered();
        }

        uint256 idx = l.poolIndex[arbiter] - 1;
        uint256 lastIdx = l.pool.length - 1;
        if (idx != lastIdx) {
            address swapped = l.pool[lastIdx];
            l.pool[idx] = swapped;
            l.poolIndex[swapped] = idx + 1;
        }
        l.pool.pop();
        delete l.poolIndex[arbiter];
        delete l.stake[arbiter];

        (bool ok,) = arbiter.call{value: staked}("");
        require(ok, "TransferFailed");

        emit ArbiterUnregistered(arbiter, staked);
    }

    function requestArbitration(uint256 invocationId, uint8 k) external nonReentrant returns (address[] memory) {
        Layout storage l = _layout();
        if (k == 0 || k % 2 == 0) {
            revert InvalidK();
        }

        Arbitration storage a = l.arbitrations[invocationId];
        if (a.status != ArbitrationStatus.NONE) {
            revert AlreadyArbitrating();
        }

        IECR.Invocation memory inv = l.executionRegistry.invocation(invocationId);
        if (inv.status != IECR.Status.ESCALATED) {
            revert InvocationNotEscalated();
        }

        if (l.pool.length < k) {
            revert PoolTooSmall();
        }

        address[] memory selected = _selectArbiters(invocationId, k, inv.executor, inv.crossVerifier);

        a.invocationId = invocationId;
        a.arbiters = selected;
        a.selectedAt = uint64(block.timestamp);
        a.commitDeadline = uint64(block.timestamp + l.commitWindow);
        a.revealDeadline = a.commitDeadline + l.revealWindow;
        a.status = ArbitrationStatus.SELECTED;

        for (uint256 i = 0; i < selected.length; i++) {
            l.selected[invocationId][selected[i]] = true;
            l.lastArbitratedAt[selected[i]][inv.executor] = block.number;
            l.lastArbitratedAt[selected[i]][inv.crossVerifier] = block.number;
        }

        emit ArbitersSelected(invocationId, selected);
        return selected;
    }

    function arbiterCommit(uint256 invocationId, bytes32 digest) external nonReentrant {
        Layout storage l = _layout();
        Arbitration storage a = l.arbitrations[invocationId];
        if (a.status != ArbitrationStatus.SELECTED && a.status != ArbitrationStatus.COMMITTING) {
            revert WrongStatus();
        }
        if (block.timestamp >= a.commitDeadline) {
            revert CommitDeadlinePassed();
        }

        address arbiter = _msgSender();
        if (!l.selected[invocationId][arbiter]) {
            revert NotAnArbiter();
        }
        if (l.committed[invocationId][arbiter]) {
            revert AlreadyCommitted();
        }

        l.commits[invocationId][arbiter] = digest;
        l.committed[invocationId][arbiter] = true;
        a.status = ArbitrationStatus.COMMITTING;

        emit ArbiterCommitted(invocationId, arbiter, digest);
    }

    function arbiterReveal(uint256 invocationId, bytes32 outputHandle, bytes32 salt) external nonReentrant {
        Layout storage l = _layout();
        Arbitration storage a = l.arbitrations[invocationId];
        if (a.status != ArbitrationStatus.COMMITTING && a.status != ArbitrationStatus.REVEALING) {
            revert WrongStatus();
        }
        if (block.timestamp < a.commitDeadline) {
            revert CommitDeadlineNotPassed();
        }
        if (block.timestamp >= a.revealDeadline) {
            revert RevealDeadlinePassed();
        }

        address arbiter = _msgSender();
        if (!l.selected[invocationId][arbiter]) {
            revert NotAnArbiter();
        }
        if (l.revealed[invocationId][arbiter]) {
            revert AlreadyRevealed();
        }
        if (!l.committed[invocationId][arbiter]) {
            revert CommitMissing();
        }

        bytes32 expected = _commitDigest(arbiter, outputHandle, salt);
        if (expected != l.commits[invocationId][arbiter]) {
            revert RevealMismatch();
        }

        l.reveals[invocationId][arbiter] = outputHandle;
        l.revealed[invocationId][arbiter] = true;
        a.status = ArbitrationStatus.REVEALING;

        emit ArbiterRevealed(invocationId, arbiter, outputHandle);
    }

    function finalize(uint256 invocationId) external nonReentrant {
        Layout storage l = _layout();
        Arbitration storage a = l.arbitrations[invocationId];
        if (a.status == ArbitrationStatus.NONE) {
            revert UnknownInvocation();
        }
        if (a.status == ArbitrationStatus.RESOLVED_MAJORITY || a.status == ArbitrationStatus.TIMED_OUT) {
            revert WrongStatus();
        }

        uint8 k = uint8(a.arbiters.length);
        uint8 majorityNeeded = (k / 2) + 1;

        if (block.timestamp < a.revealDeadline) {
            (bytes32 leader, uint8 leaderCount) = _tally(invocationId);
            if (leaderCount < majorityNeeded) {
                revert RevealDeadlineNotPassed();
            }
            a.majorityOutput = leader;
            a.majorityCount = leaderCount;
            a.status = ArbitrationStatus.RESOLVED_MAJORITY;
            emit ArbitrationResolved(invocationId, leader, leaderCount);
            return;
        }

        (bytes32 leader2, uint8 leaderCount2) = _tally(invocationId);
        if (leaderCount2 >= majorityNeeded) {
            a.majorityOutput = leader2;
            a.majorityCount = leaderCount2;
            a.status = ArbitrationStatus.RESOLVED_MAJORITY;
            emit ArbitrationResolved(invocationId, leader2, leaderCount2);
        } else {
            a.status = ArbitrationStatus.TIMED_OUT;
            emit ArbitrationTimedOut(invocationId);
        }
    }

    function arbitrationOf(uint256 invocationId) external view returns (Arbitration memory) {
        return _layout().arbitrations[invocationId];
    }

    function commitOf(uint256 invocationId, address arbiter) external view returns (bytes32) {
        return _layout().commits[invocationId][arbiter];
    }

    function revealOf(uint256 invocationId, address arbiter) external view returns (bytes32) {
        return _layout().reveals[invocationId][arbiter];
    }

    function isRegistered(address arbiter) external view returns (bool) {
        return _layout().stake[arbiter] != 0;
    }

    function poolSize() external view returns (uint256) {
        return _layout().pool.length;
    }

    function commitDigest(address arbiter, bytes32 outputHandle, bytes32 salt) external pure returns (bytes32) {
        return _commitDigest(arbiter, outputHandle, salt);
    }

    function _commitDigest(address arbiter, bytes32 outputHandle, bytes32 salt) private pure returns (bytes32) {
        return keccak256(abi.encodePacked(arbiter, outputHandle, salt));
    }

    function _selectArbiters(uint256 invocationId, uint8 k, address executor, address crossVerifier)
        private
        returns (address[] memory selected)
    {
        Layout storage l = _layout();
        uint256 poolLen = l.pool.length;
        bytes32 seed = l.randomness.randomness(keccak256(abi.encode("blindference.arbiter-selection", invocationId)));

        address[] memory candidates = new address[](poolLen);
        for (uint256 i = 0; i < poolLen; i++) {
            candidates[i] = l.pool[i];
        }

        selected = new address[](k);
        uint256 remaining = poolLen;
        uint256 chosen = 0;
        uint256 attemptCursor = 0;

        while (chosen < k && remaining > 0 && attemptCursor < poolLen * 2) {
            uint256 idx = uint256(keccak256(abi.encode(seed, attemptCursor))) % remaining;
            address candidate = candidates[idx];

            if (candidate == executor || candidate == crossVerifier) {
                _swapOutCandidate(candidates, idx, remaining);
                remaining--;
                attemptCursor++;
                continue;
            }
            if (_inCooldown(l, candidate, executor) || _inCooldown(l, candidate, crossVerifier)) {
                _swapOutCandidate(candidates, idx, remaining);
                remaining--;
                attemptCursor++;
                continue;
            }

            selected[chosen++] = candidate;
            _swapOutCandidate(candidates, idx, remaining);
            remaining--;
            attemptCursor++;
        }

        if (chosen < k) {
            revert PoolTooSmall();
        }
    }

    function _swapOutCandidate(address[] memory candidates, uint256 idx, uint256 remaining) private pure {
        if (idx != remaining - 1) {
            candidates[idx] = candidates[remaining - 1];
        }
    }

    function _inCooldown(Layout storage l, address arbiter, address subject) private view returns (bool) {
        if (l.cooldownBlocks == 0) {
            return false;
        }
        uint256 last = l.lastArbitratedAt[arbiter][subject];
        if (last == 0) {
            return false;
        }
        return block.number < last + l.cooldownBlocks;
    }

    function _tally(uint256 invocationId) private view returns (bytes32 leader, uint8 leaderCount) {
        Layout storage l = _layout();
        Arbitration storage a = l.arbitrations[invocationId];
        uint256 n = a.arbiters.length;

        for (uint256 i = 0; i < n; i++) {
            address arbiter = a.arbiters[i];
            if (!l.revealed[invocationId][arbiter]) {
                continue;
            }
            bytes32 candidate = l.reveals[invocationId][arbiter];
            uint8 count = 1;
            for (uint256 j = i + 1; j < n; j++) {
                address other = a.arbiters[j];
                if (l.revealed[invocationId][other] && l.reveals[invocationId][other] == candidate) {
                    count++;
                }
            }
            if (count > leaderCount) {
                leader = candidate;
                leaderCount = count;
            }
        }
    }

    function _layout() private pure returns (Layout storage l) {
        bytes32 slot = _LAYOUT_SLOT;
        assembly { l.slot := slot }
    }
}
