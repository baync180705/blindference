from __future__ import annotations

import hashlib


def hash_output(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def build_commitment_hash(output_cid: str, output_hash: bytes) -> str:
    return hashlib.sha256(output_cid.encode("utf-8") + output_hash).hexdigest()
