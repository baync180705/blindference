from __future__ import annotations

import pytest

from blindference_node.text_handler import process_text_task_as_leader, process_text_task_as_verifier


async def _fake_upload_to_ipfs(data: bytes) -> str:
    assert isinstance(data, bytes)
    return "bafyfakeoutputcid"


async def _fake_download_from_ipfs(_cid: str) -> bytes:
    return bytes.fromhex("001122")


@pytest.mark.asyncio
async def test_process_text_task_as_leader_builds_payload_and_posts(monkeypatch) -> None:
    from blindference_node import text_handler

    prompt_key_hex = "11" * 32
    packed_prompt = text_handler.pack_payload(
        text_handler.encrypt_text("hello private world", bytes.fromhex(prompt_key_hex))
    )

    posted: list[tuple[str, dict]] = []

    async def fake_download(cid: str) -> bytes:
        assert cid == "bafypromptcid"
        return packed_prompt

    async def fake_upload(data: bytes) -> str:
        assert isinstance(data, bytes)
        return "bafyoutputcid"

    async def fake_submit(job_id: str, payload: dict) -> dict:
        posted.append((job_id, payload))
        return {"status": "committed"}

    async def fake_model_runner(prompt: str, model_name: str | None = None) -> str:
        assert prompt == "hello private world"
        assert model_name == "gpt-4o-mini"
        return "deterministic answer"

    monkeypatch.setattr(text_handler, "download_from_ipfs", fake_download)
    monkeypatch.setattr(text_handler, "upload_to_ipfs", fake_upload)

    result = await process_text_task_as_leader(
        {
            "job_id": "job-1",
            "prompt_cid": "bafypromptcid",
            "model_id": "gpt-4o-mini",
            "encrypted_prompt_key_high": "11",
            "encrypted_prompt_key_low": "22",
        },
        fake_model_runner,
        {
            "decrypt_prompt_key": lambda _high, _low: bytes.fromhex(prompt_key_hex),
            "encrypt_output_key": lambda values: {
                "high": {"ctHash": f"enc-{values[0]}", "securityZone": 0, "utype": 8, "signature": "0x01"},
                "low": {"ctHash": f"enc-{values[1]}", "securityZone": 0, "utype": 8, "signature": "0x02"},
            },
            "submit_leader_text_result": fake_submit,
            "icl_base_url": "http://icl.local",
            "operator_address": "0x1111111111111111111111111111111111111111",
        },
    )

    assert result["output_cid"] == "bafyoutputcid"
    assert result["commitment_hash"]
    assert result["icl_response"]["status"] == "committed"
    assert posted[0][0] == "job-1"
    assert posted[0][1]["verdict"] == "CONFIRM"
    assert posted[0][1]["encrypted_output_key_high"] is not None
    assert posted[0][1]["encrypted_output_key_low"] is not None
    assert posted[0][1]["encrypted_output_key_inputs"]["high"]["signature"] == "0x01"
    assert posted[0][1]["encrypted_output_key_inputs"]["low"]["signature"] == "0x02"


@pytest.mark.asyncio
async def test_process_text_task_as_verifier_builds_payload_and_posts(monkeypatch) -> None:
    from blindference_node import text_handler

    prompt_key_hex = "22" * 32
    packed_prompt = text_handler.pack_payload(
        text_handler.encrypt_text("verify this prompt", bytes.fromhex(prompt_key_hex))
    )

    posted: list[tuple[str, dict]] = []

    async def fake_download(cid: str) -> bytes:
        assert cid == "bafyverifycid"
        return packed_prompt

    async def fake_submit(job_id: str, payload: dict) -> dict:
        posted.append((job_id, payload))
        return {"status": "committed"}

    async def fake_model_runner(prompt: str, model_name: str | None = None) -> str:
        assert prompt == "verify this prompt"
        assert model_name == "gpt-4o-mini"
        return "deterministic verifier answer"

    monkeypatch.setattr(text_handler, "download_from_ipfs", fake_download)

    expected_commitment = text_handler.build_commitment_hash(
        "bafyoutputcid",
        text_handler.hash_output("deterministic verifier answer"),
    )

    result = await process_text_task_as_verifier(
        {
            "job_id": "job-2",
            "prompt_cid": "bafyverifycid",
            "output_cid": "bafyoutputcid",
            "commitment_hash": expected_commitment,
            "model_id": "gpt-4o-mini",
            "encrypted_prompt_key_high": "33",
            "encrypted_prompt_key_low": "44",
        },
        fake_model_runner,
        {
            "decrypt_prompt_key": lambda _high, _low: bytes.fromhex(prompt_key_hex),
            "submit_verifier_text_verdict": fake_submit,
            "icl_base_url": "http://icl.local",
            "operator_address": "0x2222222222222222222222222222222222222222",
        },
    )

    assert result["commitment_hash"] == expected_commitment
    assert result["verdict"] == "CONFIRM"
    assert result["icl_response"]["status"] == "committed"
    assert posted[0][0] == "job-2"
    assert posted[0][1]["verifier_address"] == "0x2222222222222222222222222222222222222222"
