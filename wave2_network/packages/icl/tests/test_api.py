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


def build_encrypted_features(tag: str) -> tuple[list[dict[str, str]], list[str]]:
    return (
        [
            {"ctHash": f"ct-credit-{tag}", "utype": "uint32", "signature": f"sig-credit-{tag}"},
            {"ctHash": f"ct-amount-{tag}", "utype": "uint64", "signature": f"sig-amount-{tag}"},
            {"ctHash": f"ct-age-{tag}", "utype": "uint32", "signature": f"sig-age-{tag}"},
            {"ctHash": f"ct-defaults-{tag}", "utype": "uint8", "signature": f"sig-defaults-{tag}"},
        ],
        ["uint32", "uint64", "uint32", "uint8"],
    )


async def create_request(client, *, request_tag: str, min_tier: int = 0) -> dict:
    http_client, _app = client
    encrypted_features, feature_types = build_encrypted_features(request_tag)
    response = await http_client.post(
        "/v1/inference/requests",
        json={
            "developer_address": DEVELOPER_ADDRESS,
            "model_id": "groq:llama-3.3-70b-versatile",
            "encrypted_features": encrypted_features,
            "feature_types": feature_types,
            "loan_id": f"loan-{request_tag}",
            "coverage_type": "HALLUCINATION",
            "max_fee_gnk": 100,
            "min_tier": min_tier,
            "zdr_required": False,
            "verifier_count": 2,
            "metadata": {"provider": "groq", "request_tag": request_tag},
        },
    )
    assert response.status_code == 200
    return response.json()


async def create_request_with_quorum_permits(client, *, request_tag: str) -> dict:
    http_client, _app = client
    preview_response = await http_client.get(
        "/v1/inference/quorum-preview",
        params={"model_id": "groq:llama-3.3-70b-versatile", "min_tier": 0, "verifier_count": 2},
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()

    encrypted_features, feature_types = build_encrypted_features(request_tag)
    permits = [
        {"node": preview["leader"], "permit": {"mock": True, "node": preview["leader"]}},
        *[
            {"node": verifier, "permit": {"mock": True, "node": verifier}}
            for verifier in preview["verifiers"]
        ],
    ]

    response = await http_client.post(
        "/v1/inference/requests",
        json={
            "developer_address": DEVELOPER_ADDRESS,
            "model_id": "groq:llama-3.3-70b-versatile",
            "encrypted_input": encrypted_features,
            "permits": permits,
            "leader_address": preview["leader"],
            "verifier_addresses": preview["verifiers"],
            "feature_types": feature_types,
            "loan_id": f"loan-{request_tag}",
            "coverage_type": "HALLUCINATION",
            "max_fee_gnk": 100,
            "min_tier": 0,
            "zdr_required": False,
            "verifier_count": 2,
            "metadata": {"provider": "groq", "request_tag": request_tag},
        },
    )
    assert response.status_code == 200
    created = response.json()
    assert created["leader_address"] == preview["leader"]
    assert created["quorum"]["verifier_addresses"] == preview["verifiers"]
    assert len(created["metadata"]["permits"]) == 3
    return created


async def attach_permit(client, *, task_id: str, leader_address: str) -> dict:
    http_client, _app = client
    response = await http_client.patch(
        f"/v1/inference/{task_id}/permit",
        json={
            "permit": f"serialized-permit-for:{leader_address}:{task_id}",
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
    assert {"groq:llama-3.3-70b-versatile", "gemini:gemini-2.5-flash"}.issubset(model_ids)

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
async def test_quorum_preview_and_multi_recipient_submission_flow(client) -> None:
    http_client, app = client
    await bootstrap_nodes(client)
    created = await create_request_with_quorum_permits(client, request_tag=f"multi-{uuid4().hex}")

    leader_result_hash = app.state.services.chain_service.web3_client.keccak_uint256(67)
    leader_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/leader-result",
        json={
            "leader_address": created["leader_address"],
            "risk_score": 67,
            "leader_confidence": 84,
            "leader_summary": "Leader saw moderate default risk.",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "result_hash": leader_result_hash,
        },
    )
    assert leader_response.status_code == 200
    assert leader_response.json()["status"] == "leader_result_recorded"

    queued_after_leader = await http_client.get(f"/v1/inference/{created['request_id']}")
    assert queued_after_leader.status_code == 200
    queued_request = queued_after_leader.json()
    assert queued_request["status"] == "queued"
    assert queued_request["leader_submission"]["risk_score"] == 67
    assert queued_request["leader_submission"]["leader_address"] == created["leader_address"]
    assert queued_request["verifier_verdicts"] == [
        {
            "verifier_address": verifier_address,
            "submitted": False,
            "accepted": None,
            "confidence": None,
            "reason": None,
            "risk_score": None,
            "result_hash": None,
            "provider": None,
            "model": None,
            "summary": None,
            "updated_at": None,
        }
        for verifier_address in created["quorum"]["verifier_addresses"]
    ]

    first_verifier = created["quorum"]["verifier_addresses"][0]
    second_verifier = created["quorum"]["verifier_addresses"][1]

    verifier_one_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/verdicts",
        json={
            "verifier_address": first_verifier,
            "confidence": 82,
            "risk_score": 67,
            "result_hash": leader_result_hash,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "summary": "Verifier one matched the leader result.",
        },
    )
    assert verifier_one_response.status_code == 200
    assert verifier_one_response.json()["status"] == "verifier_verdict_recorded"

    queued_after_first_verifier = await http_client.get(f"/v1/inference/{created['request_id']}")
    assert queued_after_first_verifier.status_code == 200
    partially_completed = queued_after_first_verifier.json()
    assert partially_completed["status"] == "queued"
    submitted_verdicts = [verdict for verdict in partially_completed["verifier_verdicts"] if verdict["submitted"]]
    assert len(submitted_verdicts) == 1
    assert submitted_verdicts[0]["verifier_address"] == first_verifier
    assert submitted_verdicts[0]["risk_score"] == 67
    assert submitted_verdicts[0]["result_hash"] == leader_result_hash

    verifier_two_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/verdicts",
        json={
            "verifier_address": second_verifier,
            "confidence": 80,
            "risk_score": 67,
            "result_hash": leader_result_hash,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "summary": "Verifier two matched the leader result.",
        },
    )
    assert verifier_two_response.status_code == 200
    assert verifier_two_response.json()["status"] == "committed"

    finalized_response = await http_client.get(f"/v1/inference/{created['request_id']}")
    assert finalized_response.status_code == 200
    finalized = finalized_response.json()
    assert finalized["status"] == "accepted"
    assert finalized["confirm_count"] == 2
    assert finalized["reject_count"] == 0
    assert finalized["risk_score"] == 67
    assert finalized["chain_tx_hash"] is not None


@pytest.mark.asyncio
async def test_inference_request_lifecycle_commits_result_on_chain(client) -> None:
    http_client, app = client
    await bootstrap_nodes(client)
    created = await create_request(client, request_tag=f"accept-{uuid4().hex}")
    permit_attachment = await attach_permit(
        client,
        task_id=created["task_id"],
        leader_address=created["leader_address"] or created["quorum"]["leader_address"],
    )
    assert permit_attachment["status"] == "permit_attached"

    commit_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/commit",
        json={
            "risk_score": 81,
            "leader_confidence": 92,
            "leader_summary": "Applicant looks high risk due to prior defaults and leverage.",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
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
    assert request_payload["risk_score"] == 81
    assert request_payload["loan_id"].startswith("loan-accept-")
    assert request_payload["result_preview"] is not None
    assert request_payload["chain_tx_hash"] == commit_payload["chain_tx_hash"]

    chain_result = await app.state.services.chain_service.get_result(created["task_id"])
    assert chain_result["status"] == "verified"
    assert chain_result["verified_output"] == commit_payload["result_hash"]


@pytest.mark.asyncio
async def test_inference_rejection_flow_records_rejected_status(client) -> None:
    http_client, app = client
    await bootstrap_nodes(client)
    created = await create_request(client, request_tag=f"reject-{uuid4().hex}")
    await attach_permit(
        client,
        task_id=created["task_id"],
        leader_address=created["leader_address"] or created["quorum"]["leader_address"],
    )

    commit_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/commit",
        json={
            "risk_score": 22,
            "leader_confidence": 25,
            "leader_summary": "Applicant appears low risk.",
            "provider": "gemini",
            "model": "gemini-2.5-flash",
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
    created = await create_request(client, request_tag=f"dispute-{uuid4().hex}")
    await attach_permit(
        client,
        task_id=created["task_id"],
        leader_address=created["leader_address"] or created["quorum"]["leader_address"],
    )

    accepted_response = await http_client.post(
        f"/v1/inference/{created['request_id']}/commit",
        json={
            "risk_score": 64,
            "leader_confidence": 84,
            "leader_summary": "Borderline high-risk borrower.",
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
    request_payload = request_response.json()
    assert request_payload["status"] == "disputed"
    assert request_payload["metadata"]["dispute_submission_tx"].startswith("0x")
    assert request_payload["metadata"]["dispute_resolution_tx"].startswith("0x")


@pytest.mark.asyncio
async def test_inference_task_lookup_and_permit_attachment(client) -> None:
    http_client, _app = client
    await bootstrap_nodes(client)
    created = await create_request(client, request_tag=f"permit-{uuid4().hex}")

    task_lookup = await http_client.get(f"/v1/inference/task/{created['task_id']}")
    assert task_lookup.status_code == 200
    task_payload = task_lookup.json()
    assert task_payload["request_id"] == created["request_id"]
    assert task_payload["leader_address"] == created["quorum"]["leader_address"]

    attachment = await attach_permit(
        client,
        task_id=created["task_id"],
        leader_address=created["leader_address"] or created["quorum"]["leader_address"],
    )
    assert attachment["leader_address"] == created["quorum"]["leader_address"]

    refreshed = await http_client.get(f"/v1/inference/task/{created['task_id']}")
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    assert refreshed_payload["metadata"]["permits"][0]["status"] == "shared-permit-provided"


@pytest.mark.asyncio
async def test_runtime_registration_refreshes_operator_heartbeat(client) -> None:
    http_client, _app = client
    nodes = await bootstrap_nodes(client)
    target_node = nodes[0]

    runtime_registration = await http_client.post(
        "/internal/operators/runtime",
        json={
            "operator_address": target_node["operator_address"],
            "callback_url": "https://leader.example.com",
        },
    )
    assert runtime_registration.status_code == 200

    refreshed_node_response = await http_client.get(f"/v1/nodes/{target_node['operator_address']}")
    assert refreshed_node_response.status_code == 200
    refreshed_node = refreshed_node_response.json()
    assert refreshed_node["active"] is True
