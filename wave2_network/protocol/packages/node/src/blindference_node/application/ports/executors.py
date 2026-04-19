from __future__ import annotations

from typing import Protocol

from blindference_node.domain.privacy.eligibility import ExecutorEligibility


class ExecutorEligibilityProvider(Protocol):
    """Reads operator attestations from Blindference's NodeOperatorRegistry."""

    def list_eligibilities(self) -> list[ExecutorEligibility]: ...
