from __future__ import annotations

from fastapi import Header, HTTPException
from web3 import Web3


def normalize_address(address: str) -> str:
    if not Web3.is_address(address):
        raise HTTPException(status_code=400, detail=f"invalid address: {address}")
    return Web3.to_checksum_address(address)


async def verify_request(
    x_actor_address: str | None = Header(default=None, alias="X-Actor-Address"),
) -> str | None:
    if x_actor_address is None:
        return None
    return normalize_address(x_actor_address)
