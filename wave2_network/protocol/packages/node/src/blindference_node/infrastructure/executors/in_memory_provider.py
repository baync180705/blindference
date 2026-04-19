from __future__ import annotations

from collections.abc import Iterable

from blindference_node.domain.privacy.eligibility import ExecutorEligibility


class InMemoryEligibilityProvider:
    """Stand-in for reading Blindference's NodeOperatorRegistry."""

    def __init__(self, eligibilities: Iterable[ExecutorEligibility]) -> None:
        self._items = list(eligibilities)

    def list_eligibilities(self) -> list[ExecutorEligibility]:
        return list(self._items)
