from __future__ import annotations

import asyncio
import inspect
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

try:
    from blindference_utils.aes import (
        decrypt_blob,
        encrypt_text,
        generate_key,
        pack_payload,
        split_key_for_fhe,
    )
    from blindference_utils.commitment import build_commitment_hash, hash_output
    from blindference_utils.ipfs import download_from_ipfs, upload_to_ipfs
except ImportError:
    shared_py_root = Path(__file__).resolve().parents[3] / "shared-py"
    if str(shared_py_root) not in sys.path:
        sys.path.insert(0, str(shared_py_root))
    from blindference_utils.aes import (  # type: ignore[no-redef]
        decrypt_blob,
        encrypt_text,
        generate_key,
        pack_payload,
        split_key_for_fhe,
    )
    from blindference_utils.commitment import build_commitment_hash, hash_output  # type: ignore[no-redef]
    from blindference_utils.ipfs import download_from_ipfs, upload_to_ipfs  # type: ignore[no-redef]


logger = logging.getLogger("blindference.node.text")


async def process_text_task_as_leader(
    task: dict[str, Any],
    model_runner: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    prompt = await _fetch_and_decrypt_prompt(task, config)
    model_name = _resolve_model_name(task, config)
    output_text = await _run_model(model_runner, prompt, model_name)

    output_key = generate_key()
    encrypted_output = encrypt_text(output_text, output_key)
    packed_output = pack_payload(encrypted_output)
    output_cid = await _call_maybe_async(upload_to_ipfs, packed_output)
    output_hash = hash_output(output_text)
    commitment_hash = build_commitment_hash(output_cid, output_hash)

    output_key_high, output_key_low = split_key_for_fhe(output_key)
    encrypted_output_key = await _encrypt_output_key_halves(int(output_key_high), int(output_key_low), config)
    payload = {
        "job_id": _job_id(task),
        "output_cid": output_cid,
        "commitment_hash": commitment_hash,
        "encrypted_output_key_high": str(encrypted_output_key["high"]["ctHash"]),
        "encrypted_output_key_low": str(encrypted_output_key["low"]["ctHash"]),
        "encrypted_output_key_inputs": encrypted_output_key,
        "verdict": "CONFIRM",
        "confidence": 100,
    }
    response = await _submit_leader_text_result(payload["job_id"], payload, config)
    return {
        **payload,
        "prompt": prompt,
        "output_text": output_text,
        "icl_response": response,
    }


async def process_text_task_as_verifier(
    task: dict[str, Any],
    model_runner: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    prompt = await _fetch_and_decrypt_prompt(task, config)
    model_name = _resolve_model_name(task, config)
    output_text = await _run_model(model_runner, prompt, model_name)

    leader_output_cid, leader_commitment_hash = await _resolve_leader_result(task, config)
    output_hash = hash_output(output_text)
    commitment_hash = build_commitment_hash(leader_output_cid, output_hash)

    verdict = "CONFIRM" if not leader_commitment_hash or leader_commitment_hash == commitment_hash else "REJECT"
    payload = {
        "job_id": _job_id(task),
        "verifier_address": _operator_address(config, task),
        "commitment_hash": commitment_hash,
        "verdict": verdict,
        "confidence": 100 if verdict == "CONFIRM" else 0,
    }
    response = await _submit_verifier_text_verdict(payload["job_id"], payload, config)
    return {
        **payload,
        "prompt": prompt,
        "output_text": output_text,
        "icl_response": response,
    }


async def _fetch_and_decrypt_prompt(
    task: dict[str, Any],
    config: dict[str, Any],
) -> str:
    prompt_cid = _resolve_prompt_cid(task)
    packed_prompt = await _call_maybe_async(download_from_ipfs, prompt_cid)

    decrypt_prompt_key = config.get("decrypt_prompt_key")
    if callable(decrypt_prompt_key):
        prompt_key = await _call_maybe_async(
            decrypt_prompt_key,
            _resolve_prompt_key_handle(task, "high"),
            _resolve_prompt_key_handle(task, "low"),
        )
    else:
        key_hex = _resolve_prompt_key_hex(task, config)
        if not key_hex:
            raise ValueError(
                "Text prompt decryption requires a CoFHE prompt-key decryptor or a test stub key."
            )
        prompt_key = bytes.fromhex(key_hex)

    return decrypt_blob(packed_prompt, prompt_key)


async def _encrypt_output_key_halves(
    high: int,
    low: int,
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    encrypt_output_key = config.get("encrypt_output_key")
    if callable(encrypt_output_key):
        result = await _call_maybe_async(encrypt_output_key, [high, low])
        if not isinstance(result, dict) or "high" not in result or "low" not in result:
            raise ValueError("encrypt_output_key must return a dict with high and low encrypted inputs")
        return {
            "high": dict(result["high"]),
            "low": dict(result["low"]),
        }

    return {
        "high": {"ctHash": str(high), "securityZone": 0, "utype": 8, "signature": "0x"},
        "low": {"ctHash": str(low), "securityZone": 0, "utype": 8, "signature": "0x"},
    }


async def _submit_leader_text_result(job_id: str, payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    submitter = config.get("submit_leader_text_result")
    if callable(submitter):
        return await _call_maybe_async(submitter, job_id, payload)
    return await _post_json(config, "/internal/task/result", payload)


async def _submit_verifier_text_verdict(job_id: str, payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    submitter = config.get("submit_verifier_text_verdict")
    if callable(submitter):
        return await _call_maybe_async(submitter, job_id, payload)
    return await _post_json(config, "/internal/task/verify", payload)


async def _post_json(config: dict[str, Any], path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base_url = str(config["icl_base_url"]).rstrip("/")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.post(path, json=payload)
        response.raise_for_status()
        return response.json()


async def _get_json(config: dict[str, Any], path: str) -> dict[str, Any]:
    base_url = str(config["icl_base_url"]).rstrip("/")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.get(path)
        response.raise_for_status()
        return response.json()


async def _run_model(model_runner: Any, prompt: str, model_name: str) -> str:
    result = model_runner(prompt, model_name=model_name)
    if inspect.isawaitable(result):
        result = await result
    return str(result)


async def _call_maybe_async(function: Any, *args: Any, **kwargs: Any) -> Any:
    result = function(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _resolve_prompt_cid(task: dict[str, Any]) -> str:
    prompt_cid = task.get("prompt_cid")
    if isinstance(prompt_cid, str) and prompt_cid:
        return prompt_cid

    text_request = task.get("text_request")
    if isinstance(text_request, dict):
        nested = text_request.get("prompt_cid") or text_request.get("promptCID")
        if isinstance(nested, str) and nested:
            return nested

    raise ValueError("Text task is missing prompt_cid")


def _resolve_prompt_key_hex(task: dict[str, Any], config: dict[str, Any]) -> str | None:
    metadata = task.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("text_stub_prompt_key_hex")
        if isinstance(value, str) and value:
            return value.removeprefix("0x")

    value = config.get("text_stub_prompt_key_hex")
    if isinstance(value, str) and value:
        return value.removeprefix("0x")
    return None


def _resolve_prompt_key_handle(task: dict[str, Any], half: str) -> str:
    field_name = f"encrypted_prompt_key_{half}"
    value = task.get(field_name)
    if isinstance(value, str) and value:
        return value

    text_request = task.get("text_request")
    if isinstance(text_request, dict):
        encrypted_key = text_request.get("encrypted_prompt_key") or text_request.get("encryptedPromptKey")
        if isinstance(encrypted_key, dict):
            nested = encrypted_key.get(half)
            if isinstance(nested, str) and nested:
                return nested

    raise ValueError(f"Text task is missing encrypted prompt-key {half} handle")


def _resolve_model_name(task: dict[str, Any], config: dict[str, Any]) -> str:
    text_request = task.get("text_request")
    if isinstance(text_request, dict):
        model_id = text_request.get("model_id")
        if isinstance(model_id, str) and model_id:
            return model_id

    model_id = task.get("model_id")
    if isinstance(model_id, str) and model_id:
        return model_id

    configured = config.get("llm_model")
    if isinstance(configured, str) and configured:
        return configured

    return "gpt-4o-mini"


def _resolve_leader_output_cid(task: dict[str, Any]) -> str:
    output_cid = task.get("output_cid")
    if isinstance(output_cid, str) and output_cid:
        return output_cid

    metadata = task.get("metadata")
    if isinstance(metadata, dict):
        leader_result = metadata.get("text_leader_result")
        if isinstance(leader_result, dict):
            nested = leader_result.get("output_cid")
            if isinstance(nested, str) and nested:
                return nested

    raise ValueError("Verifier text task is missing leader output_cid")


def _resolve_leader_commitment_hash(task: dict[str, Any]) -> str | None:
    commitment_hash = task.get("commitment_hash")
    if isinstance(commitment_hash, str) and commitment_hash:
        return commitment_hash

    metadata = task.get("metadata")
    if isinstance(metadata, dict):
        leader_result = metadata.get("text_leader_result")
        if isinstance(leader_result, dict):
            nested = leader_result.get("commitment_hash")
            if isinstance(nested, str) and nested:
                return nested
    return None


async def _resolve_leader_result(task: dict[str, Any], config: dict[str, Any]) -> tuple[str, str | None]:
    try:
        return _resolve_leader_output_cid(task), _resolve_leader_commitment_hash(task)
    except ValueError:
        pass

    job_id = _job_id(task)
    poll_interval = float(config.get("leader_result_poll_interval_seconds", 2.0))
    attempts = int(config.get("leader_result_poll_attempts", 15))

    for _ in range(attempts):
        status = await _get_json(config, f"/v1/inference/{job_id}")
        output_cid = status.get("output_cid")
        if isinstance(output_cid, str) and output_cid:
            commitment_hash = status.get("commitment_hash")
            return output_cid, commitment_hash if isinstance(commitment_hash, str) and commitment_hash else None
        await asyncio.sleep(poll_interval)

    raise ValueError("Verifier text task could not find leader output_cid from ICL status")


def _operator_address(config: dict[str, Any], task: dict[str, Any]) -> str:
    address = config.get("operator_address")
    if isinstance(address, str) and address:
        return address

    metadata = task.get("metadata")
    if isinstance(metadata, dict):
        address = metadata.get("operator_address")
        if isinstance(address, str) and address:
            return address

    raise ValueError("Missing operator address for text verifier submission")


def _job_id(task: dict[str, Any]) -> str:
    for key in ("job_id", "request_id"):
        value = task.get(key)
        if isinstance(value, str) and value:
            return value
    raise ValueError("Task is missing job_id/request_id")
