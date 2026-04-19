from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...
    def epoch_seconds(self) -> int: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)

    def epoch_seconds(self) -> int:
        return int(self.now().timestamp())
