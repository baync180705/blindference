from __future__ import annotations

from uuid import uuid4

import pytest

from tests.test_api import DEVELOPER_ADDRESS, bootstrap_nodes


@pytest.mark.asyncio
async def test_text_inference_job_is_persisted_and_returned_from_status_poll(client) -> None:
    http_client, _app = client
    await bootstrap_nodes(client)

    prompt_cid = f"bafytextprompt{uuid4().hex}"
    encrypted_high = "340282366920938463463374607431768211455"
    encrypted_low = "42"

    create_response = await http_client.post(
        "/v1/inference/requests",
        json={
            "developer_address": DEVELOPER_ADDRESS,
            "mode": "text",
            "text_request": {
                "prompt_cid": prompt_cid,
                "encrypted_prompt_key": {
                    "high": encrypted_high,
                    "low": encrypted_low,
                },
                "model_id": "gpt-4o-mini",
                "coverage_enabled": True,
            },
            "min_tier": 0,
            "zdr_required": False,
            "verifier_count": 2,
            "metadata": {"request_tag": "text-mode"},
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["job_id"]

    status_response = await http_client.get(f"/v1/inference/{created['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == created["job_id"]
    assert status_payload["status"] == "QUEUED"
    assert status_payload["output_cid"] is None
    assert status_payload["commitment_hash"] is None
    assert status_payload["quorum"]["confirmations"] == 0
    assert status_payload["quorum"]["confidence"] == 0
    assert len(status_payload["quorum"]["verifier_addresses"]) == 2


@pytest.mark.asyncio
async def test_text_inference_internal_result_and_verifier_submissions_reach_quorum(client) -> None:
    http_client, app = client
    await bootstrap_nodes(client)

    create_response = await http_client.post(
        "/v1/inference/requests",
        json={
            "developer_address": DEVELOPER_ADDRESS,
            "mode": "text",
            "text_request": {
                "prompt_cid": f"bafytextprompt{uuid4().hex}",
                "encrypted_prompt_key": {
                    "high": "111",
                    "low": "222",
                },
                "model_id": "gpt-4o-mini",
                "coverage_enabled": False,
            },
            "min_tier": 0,
            "zdr_required": False,
            "verifier_count": 2,
            "metadata": {"request_tag": "text-internal"},
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    internal_request = await app.state.services.quorum_service.get_request(created["job_id"])
    verifiers = internal_request.quorum.verifier_addresses

    leader_result = await http_client.post(
        "/internal/task/result",
        json={
            "job_id": created["job_id"],
            "output_cid": f"bafyoutput{uuid4().hex}",
            "commitment_hash": "0xabc123",
            "encrypted_output_key_high": "333",
            "encrypted_output_key_low": "444",
            "encrypted_output_key_inputs": {
                "high": {"ctHash": "333", "securityZone": 0, "utype": 8, "signature": "0x"},
                "low": {"ctHash": "444", "securityZone": 0, "utype": 8, "signature": "0x"},
            },
            "verdict": "CONFIRM",
            "confidence": 93,
        },
    )
    assert leader_result.status_code == 200
    assert leader_result.json()["status"] == "leader_result_recorded"
    assert leader_result.json()["output_key_store_tx"]

    verifier_result = await http_client.post(
        "/internal/task/verify",
        json={
            "job_id": created["job_id"],
            "verifier_address": verifiers[0],
            "commitment_hash": "0xabc123",
            "verdict": "CONFIRM",
            "confidence": 88,
        },
    )
    assert verifier_result.status_code == 200
    assert verifier_result.json()["status"] == "committed"

    status_response = await http_client.get(f"/v1/inference/{created['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "ACCEPTED"
    assert status_payload["output_cid"].startswith("bafyoutput")
    assert status_payload["commitment_hash"] == "0xabc123"
    assert status_payload["encrypted_output_key_high"] == "333"
    assert status_payload["encrypted_output_key_low"] == "444"
    assert status_payload["quorum"]["confirmations"] == 2
    assert status_payload["quorum"]["confidence"] == 90

    internal_request = await app.state.services.quorum_service.get_request(created["job_id"])
    assert internal_request.metadata["output_key_store_tx"]
    assert internal_request.metadata["output_key_store_job_id"]
    assert internal_request.metadata["output_key_store_address"] == app.state.services.chain_service.settings.PROMPT_KEY_STORE_ADDRESS
