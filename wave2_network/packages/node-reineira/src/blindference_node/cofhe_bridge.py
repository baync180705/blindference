from __future__ import annotations

import asyncio
import json
from pathlib import Path

from eth_account import Account


class CofheBridgeError(RuntimeError):
    pass


class CofheBridgeClient:
    def __init__(self, *, script_path: str, rpc_url: str, chain_id: int, private_key: str):
        self.script_path = script_path
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.private_key = private_key
        self.operator_address = Account.from_key(private_key).address

    async def decrypt_for_view(self, *, encrypted_features: list[dict], permit: str) -> list[int]:
        payload = {
            "action": "decrypt_for_view",
            "rpcUrl": self.rpc_url,
            "chainId": self.chain_id,
            "privateKey": self.private_key,
            "permit": permit,
            "features": [
                {
                    "ctHash": str(feature.get("ct_hash") or feature.get("ctHash")),
                    "utype": feature.get("utype"),
                }
                for feature in encrypted_features
            ],
        }
        result = await self._run(payload)
        return [int(value) for value in result["values"]]

    async def _run(self, payload: dict) -> dict:
        process = await asyncio.create_subprocess_exec(
            "node",
            self.script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path(self.script_path).resolve().parent.parent),
        )
        stdout, stderr = await process.communicate(json.dumps(payload).encode("utf-8"))
        output = stdout.decode("utf-8").strip().splitlines()
        if not output:
            raise CofheBridgeError(stderr.decode("utf-8").strip() or "CoFHE bridge produced no output")

        response = json.loads(output[-1])
        if process.returncode != 0 or not response.get("ok"):
            raise CofheBridgeError(response.get("error") or stderr.decode("utf-8").strip() or "CoFHE bridge failed")
        return response
