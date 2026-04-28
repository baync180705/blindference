from __future__ import annotations

import os

from Crypto.Cipher import AES


def generate_key() -> bytes:
    return os.urandom(32)


def encrypt_text(text: str, key: bytes) -> dict[str, bytes]:
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")

    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, auth_tag = cipher.encrypt_and_digest(text.encode("utf-8"))

    return {
        "iv": iv,
        "authTag": auth_tag,
        "ciphertext": ciphertext,
    }


def pack_payload(payload: dict[str, bytes]) -> bytes:
    iv = payload["iv"]
    auth_tag = payload["authTag"]
    ciphertext = payload["ciphertext"]

    if len(iv) != 16:
        raise ValueError("IV must be 16 bytes")
    if len(auth_tag) != 16:
        raise ValueError("Auth tag must be 16 bytes")

    return iv + auth_tag + ciphertext


def unpack_payload(packed: bytes) -> dict[str, bytes]:
    if len(packed) < 32:
        raise ValueError("Packed data too short")

    return {
        "iv": packed[:16],
        "authTag": packed[16:32],
        "ciphertext": packed[32:],
    }


def decrypt_blob(packed: bytes, key: bytes) -> str:
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")

    payload = unpack_payload(packed)
    cipher = AES.new(key, AES.MODE_GCM, nonce=payload["iv"])
    plaintext = cipher.decrypt_and_verify(payload["ciphertext"], payload["authTag"])
    return plaintext.decode("utf-8")


def split_key_for_fhe(key: bytes) -> tuple[int, int]:
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")

    high = int.from_bytes(key[:16], "big")
    low = int.from_bytes(key[16:], "big")
    return high, low


def combine_key_from_fhe(high: int, low: int) -> bytes:
    return high.to_bytes(16, "big") + low.to_bytes(16, "big")
