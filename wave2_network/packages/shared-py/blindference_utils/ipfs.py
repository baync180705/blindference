from __future__ import annotations

import os

import requests


def _api_key() -> str:
    api_key = os.getenv("LIGHTHOUSE_API_KEY")
    if not api_key:
        raise RuntimeError("LIGHTHOUSE_API_KEY is not set")
    return api_key


def upload_to_ipfs(data: bytes) -> str:
    response = requests.post(
        "https://node.lighthouse.storage/api/v0/add",
        files={"file": ("blob", data)},
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=60,
    )
    response.raise_for_status()

    payload = response.json()
    cid = payload.get("Hash")
    if not cid:
        raise RuntimeError(f"IPFS upload failed: {payload}")

    return str(cid)


def download_from_ipfs(cid: str) -> bytes:
    response = requests.get(
        f"https://gateway.lighthouse.storage/ipfs/{cid}",
        timeout=60,
    )
    response.raise_for_status()
    return response.content
