from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

from eth_utils import to_checksum_address

AgentId = NewType("AgentId", int)
InvocationId = NewType("InvocationId", int)
EscrowId = NewType("EscrowId", int)
TicketId = NewType("TicketId", bytes)


@dataclass(frozen=True, slots=True)
class NodeAddress:
    """Checksummed Ethereum address of a Blindference node."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", to_checksum_address(self.value))
