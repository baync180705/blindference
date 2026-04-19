from __future__ import annotations

from uuid import uuid4

import pytest


DEVELOPER_ADDRESS = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"


async def bootstrap_nodes(client) -> list[dict]:
    http_client, _app = client
    response = await http_client.post("/admin/bootstrap-demo-nodes")
    assert response.status_code == 200

    nodes_response = await http_client.get("/v1/nodes/active")
    assert nodes_response.status_code == 200
    nodes = nodes_response.json()
    assert len(nodes) >= 3
    return nodes


async def create_request(client, *, prompt: str, min_tier: int = 0) -> dict:
    http_client, _app = client
    response = await http_client.post(
        "/v1/inference/requests",
        json={
            "developer_address": DEVELOPER_ADDRESS,
            "model_id": "groq-llm-default",
            "prompt": prompt,
            "min_tier": min_tier,
            "zdr_required": False,
            "verifier_count": 2,
            "metadata": {"provider": "groq", "request_tag": prompt},
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_health_and_admin_status(client) -> None:
    http_client, _app = client

    health_response = await http_client.get("/health")
    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert health_payload["status"] == "ok"
    assert health_payload["chain_connected"] is True

    status_response = await http_client.get("/admin/status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["chain_connected"] is True
    assert "inference_requests" in status_payload["collections"]


@pytest.mark.asyncio
async def test_bootstrap_nodes_and_filter_active_list(client) -> None:
    http_client, _app = client
    nodes = await bootstrap_nodes(client)

    assert any(node["zdr_compliant"] for node in nodes)
    assert all(node["active"] is True for node in nodes)

    zdr_response = await http_client.get("/v1/nodes/active", params={"zdr_required": "true"})
    assert zdr_response.status_code == 200
    zdr_nodes = zdr_response.json()
    assert zdr_nodes
    assert all(node["zdr_compliant"] is True for node in zdr_nodes)

    tier_two_response = await http_client.get("/v1/nodes/active", params={"min_tier": 2})
    assert tier_two_response.status_code == 200
    tier_two_nodes = tier_two_response.json()
    assert len(tier_two_nodes) == 1
    assert tier_two_nodes[0]["model_tiers"] == [2]


@pytest.mark.asyncio
async def test_models_endpoint_exposes_defaults_and_registration(client) -> None:
    http_client, _app = client

    list_response = await http_client.get("/v1/models")
    assert list_response.status_code == 200
    model_ids = {model["model_id"] for model in list_response.json()}
    assert {"groq-llm-default", "gemini-llm-default"}.issubset(model_ids)

    custom_model_id = f"gemini-proxy-{uuid4().hex[:8]}"
    register_response = await http_client.post(
        "/v1/models",
        json={
            "model_id": custom_model_id,
            "name": "Gemini Proxy",
            "provider": "google-gemini",
            "min_tier": 0,
            "zdr_required": True,
            "metadata": {"mode": "hosted-api"},
        },
    )
    assert register_response.status_code == 200
    registered_model = register_response.json()
    assert registered_model["model_id"] == custom_model_id
    assert registered_model["zdr_required"] is True


@pytest.mark.asyncio
async def test_inference_request_lifecycle_commits_result_on_chain(client) -> None:
    http_client, app = client
    await bootstrap_nodes(client)
    created = await create_request(client, prompt=f"accept-{uuid4().hex}")

    commit_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/commit",
        json={
            "leader_output": "Hosted model response",
            "leader_confidence": 92,
            "verifier_verdicts": [
                {
                    "verifier_address": created["quorum"]["verifier_addresses"][0],
                    "accepted": True,
                    "confidence": 91,
                    "reason": None,
                },
                {
                    "verifier_address": created["quorum"]["verifier_addresses"][1],
                    "accepted": True,
                    "confidence": 89,
                    "reason": None,
                },
            ],
            "rejection_reason": None,
        },
    )
    assert commit_response.status_code == 200
    commit_payload = commit_response.json()
    assert commit_payload["accepted"] is True
    assert commit_payload["confirm_count"] == 2
    assert commit_payload["reject_count"] == 0
    assert commit_payload["aggregated_confidence"] == 91

    request_response = await http_client.get(f"/v1/inference/{created['request_id']}")
    assert request_response.status_code == 200
    request_payload = request_response.json()
    assert request_payload["status"] == "accepted"
    assert request_payload["result_preview"] == "Hosted model response"
    assert request_payload["chain_tx_hash"] == commit_payload["chain_tx_hash"]

    chain_result = await app.state.services.chain_service.get_result(created["task_id"])
    assert chain_result["status"] == "verified"
    assert chain_result["verified_output"] == commit_payload["result_hash"]


@pytest.mark.asyncio
async def test_inference_rejection_flow_records_rejected_status(client) -> None:
    http_client, app = client
    await bootstrap_nodes(client)
    created = await create_request(client, prompt=f"reject-{uuid4().hex}")

    commit_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/commit",
        json={
            "leader_output": "Low confidence answer",
            "leader_confidence": 25,
            "verifier_verdicts": [
                {
                    "verifier_address": created["quorum"]["verifier_addresses"][0],
                    "accepted": False,
                    "confidence": 20,
                    "reason": "inconsistent output",
                },
                {
                    "verifier_address": created["quorum"]["verifier_addresses"][1],
                    "accepted": False,
                    "confidence": 18,
                    "reason": "policy mismatch",
                },
            ],
            "rejection_reason": "quorum rejected output",
        },
    )
    assert commit_response.status_code == 200
    commit_payload = commit_response.json()
    assert commit_payload["accepted"] is False
    assert commit_payload["confirm_count"] == 0
    assert commit_payload["reject_count"] == 2

    request_response = await http_client.get(f"/v1/inference/{created['request_id']}")
    assert request_response.status_code == 200
    request_payload = request_response.json()
    assert request_payload["status"] == "rejected"

    chain_result = await app.state.services.chain_service.get_result(created["task_id"])
    assert chain_result["status"] == "escalated"


@pytest.mark.asyncio
async def test_dispute_submission_for_accepted_request(client) -> None:
    http_client, _app = client
    await bootstrap_nodes(client)
    created = await create_request(client, prompt=f"dispute-{uuid4().hex}")

    accepted_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/commit",
        json={
            "leader_output": "Potentially disputable answer",
            "leader_confidence": 84,
            "verifier_verdicts": [],
            "rejection_reason": None,
        },
    )
    assert accepted_response.status_code == 200

    dispute_response = await http_client.post(
        f"/v1/disputes/{created['request_id']}",
        json={
            "developer_address": DEVELOPER_ADDRESS,
            "evidence_hash": f"0x{uuid4().hex}{uuid4().hex}",
            "evidence_uri": "ipfs://blindference-dispute-evidence",
            "notes": "manual review requested",
        },
    )
    assert dispute_response.status_code == 200
    dispute_payload = dispute_response.json()
    assert dispute_payload["request_id"] == created["request_id"]
    assert dispute_payload["developer_address"] == DEVELOPER_ADDRESS

    fetched_dispute = await http_client.get(f"/v1/disputes/{created['request_id']}")
    assert fetched_dispute.status_code == 200
    assert fetched_dispute.json()["evidence_uri"] == "ipfs://blindference-dispute-evidence"

    request_response = await http_client.get(f"/v1/inference/{created['request_id']}")
    assert request_response.status_code == 200
    assert request_response.json()["status"] == "disputed"
