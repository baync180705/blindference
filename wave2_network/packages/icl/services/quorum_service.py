from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging

import httpx

from db.collections import (
    DISPUTES,
    INFERENCE_REQUESTS,
    NODE_RUNTIMES,
    PERMITS,
    QUORUM_ASSIGNMENTS,
    QUORUM_CERTIFICATES,
    VERIFIER_VERDICTS,
)
from models.db_models import (
    DisputeRecord,
    InferenceRequestRecord,
    PermitEntryRecord,
    PermitRecord,
    QuorumAssignmentRecord,
    QuorumCertificateRecord,
    NodeRuntimeRecord,
    VerifierVerdictRecord,
)
from models.internal_models import LeaderTextResultSubmission, VerifierTextVerdict
from models.request_models import (
    DisputeSubmissionRequest,
    InferenceCommitRequest,
    InferencePermitAttachmentRequest,
    InferenceRequestCreate,
    LeaderResultSubmissionRequest,
    VerifierVerdictInput,
    VerifierVerdictSubmissionRequest,
)
from models.response_models import (
    EncryptedFeatureResponse,
    InferenceCommitResponse,
    InferenceRequestResponse,
    LeaderSubmissionResponse,
    QuorumAssignmentResponse,
    VerifierVerdictResponse,
)
from models.text_inference import QuorumCertificate, TextInferenceRequest, TextInferenceResult
from services.chain_service import ChainService
from services.node_selector import NodeSelector
from services.verdict_aggregator import VerdictAggregator


logger = logging.getLogger("blindference.icl.quorum")


class QuorumService:
    def __init__(
        self,
        database,
        chain_service: ChainService,
        node_selector: NodeSelector,
        verdict_aggregator: VerdictAggregator,
    ):
        self.database = database
        self.chain_service = chain_service
        self.node_selector = node_selector
        self.verdict_aggregator = verdict_aggregator

    def _is_text_mode(self, payload: InferenceRequestCreate) -> bool:
        return payload.mode.lower() == "text"

    async def preview_quorum(
        self,
        *,
        min_tier: int,
        zdr_required: bool,
        verifier_count: int,
    ) -> dict[str, list[str] | str]:
        return await self.node_selector.select_quorum(
            min_tier=min_tier,
            zdr_required=zdr_required,
            verifier_count=verifier_count,
        )

    async def create_request(self, payload: InferenceRequestCreate) -> InferenceRequestResponse:
        if self._is_text_mode(payload):
            return await self._create_text_request(payload)
        return await self._create_risk_request(payload)

    async def create_request_status(self, payload: InferenceRequestCreate) -> InferenceRequestResponse | TextInferenceResult:
        response = await self.create_request(payload)
        if self._is_text_mode(payload):
            return await self.get_request_status(response.request_id)
        return response

    async def _create_risk_request(self, payload: InferenceRequestCreate) -> InferenceRequestResponse:
        selected_quorum = await self.preview_quorum(
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
        )
        quorum = self._resolve_requested_quorum(payload, selected_quorum)
        encrypted_features = payload.normalized_encrypted_features()
        if not encrypted_features:
            raise ValueError("encrypted_input or encrypted_features is required")

        required_nodes = [
            quorum["leader_address"],
            *list(quorum["verifier_addresses"]),
        ]
        normalized_permits = self._normalize_permit_entries(payload.permits)
        if normalized_permits:
            missing_nodes = [
                node_address
                for node_address in required_nodes
                if node_address not in {permit.node_address for permit in normalized_permits}
            ]
            if missing_nodes:
                raise ValueError(
                    f"missing permits for quorum members: {', '.join(missing_nodes)}"
                )

        now = datetime.now(timezone.utc)
        feature_fingerprint = json.dumps(
            {
                "features": [feature.to_wire() for feature in encrypted_features],
                "feature_types": payload.feature_types,
                "loan_id": payload.loan_id,
                "model_id": payload.model_id,
            },
            sort_keys=True,
        )
        task_id = self.chain_service.web3_client.keccak_text(
            f"{payload.developer_address}:{feature_fingerprint}:{now.isoformat()}"
        )
        metadata = dict(payload.metadata)
        metadata["coverage_requested"] = bool(payload.coverage_type)

        request_record = InferenceRequestRecord(
            task_id=task_id,
            invocation_id=self.chain_service.web3_client.task_id_to_invocation_id(task_id),
            developer_address=self.chain_service.web3_client.checksum_address(payload.developer_address),
            model_id=payload.model_id,
            encrypted_features=[feature.to_wire() for feature in encrypted_features],
            feature_types=list(payload.feature_types),
            loan_id=payload.loan_id,
            coverage_type=payload.coverage_type,
            max_fee_gnk=payload.max_fee_gnk,
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
            leader_address=quorum["leader_address"],
            verifier_addresses=list(quorum["verifier_addresses"]),
            metadata=metadata,
            dispute_deadline=now + timedelta(hours=72),
        )
        assignment_record = QuorumAssignmentRecord(
            request_id=request_record.request_id,
            task_id=request_record.task_id,
            leader_address=quorum["leader_address"],
            verifier_addresses=list(quorum["verifier_addresses"]),
            candidate_addresses=list(quorum["candidate_addresses"]),
        )

        await self.database[INFERENCE_REQUESTS].insert_one(request_record.model_dump())
        await self.database[QUORUM_ASSIGNMENTS].insert_one(assignment_record.model_dump())
        if normalized_permits:
            await self.database[PERMITS].update_one(
                {"task_id": request_record.task_id},
                {
                    "$set": PermitRecord(
                        task_id=request_record.task_id,
                        permits=normalized_permits,
                    ).model_dump()
                },
                upsert=True,
            )
        chain_registration = await self.chain_service.register_task(
            task_id=request_record.task_id,
            developer_address=request_record.developer_address,
            leader_address=assignment_record.leader_address,
            cross_verifier_address=assignment_record.verifier_addresses[0],
            model_id=request_record.model_id,
        )
        if normalized_permits:
            metadata["permits"] = [self._permit_record_to_metadata(entry) for entry in normalized_permits]
        registration_tx_hash = chain_registration.get("tx_hash")
        metadata["task_registered_tx"] = registration_tx_hash
        metadata["escrow_creation_tx"] = (
            registration_tx_hash
            or self.chain_service.web3_client.ensure_hex_prefix(
                self.chain_service.web3_client.keccak_text(f"mock-escrow-create:{request_record.task_id}")
            )
        )
        if payload.coverage_type:
            metadata["coverage_id"] = metadata.get("coverage_id") or f"cov_{request_record.request_id[:10]}"
            metadata["coverage_purchase_tx"] = (
                registration_tx_hash
                or self.chain_service.web3_client.ensure_hex_prefix(
                    self.chain_service.web3_client.keccak_text(f"mock-coverage-purchase:{request_record.task_id}")
                )
            )
        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_record.request_id},
            {
                "$set": {
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        await self._dispatch_request_to_quorum(request_record.request_id)
        return await self.get_request(request_record.request_id)

    async def _create_text_request(self, payload: InferenceRequestCreate) -> InferenceRequestResponse:
        if payload.text_request is None:
            raise ValueError("text_request is required when mode='text'")

        selected_quorum = await self.preview_quorum(
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
        )
        quorum = self._resolve_requested_quorum(payload, selected_quorum)

        effective_model_id = payload.text_request.model_id or payload.model_id or "text-inference"
        required_nodes = [
            quorum["leader_address"],
            *list(quorum["verifier_addresses"]),
        ]
        normalized_permits = self._normalize_permit_entries(payload.permits)
        if normalized_permits:
            missing_nodes = [
                node_address
                for node_address in required_nodes
                if node_address not in {permit.node_address for permit in normalized_permits}
            ]
            if missing_nodes:
                raise ValueError(
                    f"missing permits for quorum members: {', '.join(missing_nodes)}"
                )

        now = datetime.now(timezone.utc)
        text_fingerprint = json.dumps(
            {
                "prompt_cid": payload.text_request.prompt_cid,
                "encrypted_prompt_key": {
                    "high": payload.text_request.encrypted_prompt_key.high,
                    "low": payload.text_request.encrypted_prompt_key.low,
                },
                "model_id": effective_model_id,
            },
            sort_keys=True,
        )
        task_id = self.chain_service.web3_client.keccak_text(
            f"{payload.developer_address}:{text_fingerprint}:{now.isoformat()}"
        )
        metadata = dict(payload.metadata)
        metadata["coverage_requested"] = bool(payload.text_request.coverage_enabled or payload.coverage_type)
        metadata["text_request"] = {
            "prompt_cid": payload.text_request.prompt_cid,
            "encrypted_prompt_key": {
                "high": payload.text_request.encrypted_prompt_key.high,
                "low": payload.text_request.encrypted_prompt_key.low,
            },
            "model_id": payload.text_request.model_id,
            "coverage_enabled": payload.text_request.coverage_enabled,
        }

        request_record = InferenceRequestRecord(
            task_id=task_id,
            invocation_id=self.chain_service.web3_client.task_id_to_invocation_id(task_id),
            developer_address=self.chain_service.web3_client.checksum_address(payload.developer_address),
            model_id=effective_model_id,
            mode="text",
            text_mode=True,
            encrypted_features=[],
            feature_types=list(payload.feature_types),
            loan_id=payload.loan_id,
            coverage_type=payload.coverage_type,
            max_fee_gnk=payload.max_fee_gnk,
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
            leader_address=quorum["leader_address"],
            verifier_addresses=list(quorum["verifier_addresses"]),
            metadata=metadata,
            prompt_cid=payload.text_request.prompt_cid,
            encrypted_prompt_key_high=payload.text_request.encrypted_prompt_key.high,
            encrypted_prompt_key_low=payload.text_request.encrypted_prompt_key.low,
            dispute_deadline=now + timedelta(hours=72),
        )
        assignment_record = QuorumAssignmentRecord(
            request_id=request_record.request_id,
            task_id=request_record.task_id,
            leader_address=quorum["leader_address"],
            verifier_addresses=list(quorum["verifier_addresses"]),
            candidate_addresses=list(quorum["candidate_addresses"]),
        )

        await self.database[INFERENCE_REQUESTS].insert_one(request_record.model_dump())
        await self.database[QUORUM_ASSIGNMENTS].insert_one(assignment_record.model_dump())
        if normalized_permits:
            await self.database[PERMITS].update_one(
                {"task_id": request_record.task_id},
                {
                    "$set": PermitRecord(
                        task_id=request_record.task_id,
                        permits=normalized_permits,
                    ).model_dump()
                },
                upsert=True,
            )
            metadata["permits"] = [self._permit_record_to_metadata(entry) for entry in normalized_permits]

        chain_registration = await self.chain_service.register_task(
            task_id=request_record.task_id,
            developer_address=request_record.developer_address,
            leader_address=assignment_record.leader_address,
            cross_verifier_address=assignment_record.verifier_addresses[0],
            model_id=request_record.model_id,
        )
        registration_tx_hash = chain_registration.get("tx_hash")
        metadata["task_registered_tx"] = registration_tx_hash

        prompt_key_inputs = self._resolve_text_prompt_key_inputs(
            metadata,
            fallback_high_handle=payload.text_request.encrypted_prompt_key.high,
            fallback_low_handle=payload.text_request.encrypted_prompt_key.low,
        )
        prompt_key_store = await self.chain_service.store_text_prompt_key(
            task_id=request_record.task_id,
            encrypted_high_input=prompt_key_inputs["high"],
            encrypted_low_input=prompt_key_inputs["low"],
            allowed_nodes=required_nodes,
        )
        metadata["prompt_key_store_address"] = self.chain_service.settings.PROMPT_KEY_STORE_ADDRESS
        metadata["prompt_key_store_tx"] = prompt_key_store.get("tx_hash")
        metadata["prompt_key_store_status"] = prompt_key_store.get("status")

        metadata["escrow_creation_tx"] = (
            registration_tx_hash
            or self.chain_service.web3_client.ensure_hex_prefix(
                self.chain_service.web3_client.keccak_text(f"mock-escrow-create:{request_record.task_id}")
            )
        )
        if payload.text_request.coverage_enabled or payload.coverage_type:
            metadata["coverage_id"] = metadata.get("coverage_id") or f"cov_{request_record.request_id[:10]}"
            metadata["coverage_purchase_tx"] = (
                registration_tx_hash
                or self.chain_service.web3_client.ensure_hex_prefix(
                    self.chain_service.web3_client.keccak_text(f"mock-coverage-purchase:{request_record.task_id}")
                )
            )
        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_record.request_id},
            {
                "$set": {
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        await self._dispatch_request_to_quorum(request_record.request_id)
        return await self.get_request(request_record.request_id)

    async def list_requests(self) -> list[InferenceRequestResponse]:
        cursor = self.database[INFERENCE_REQUESTS].find({})
        documents: list[dict] = []
        async for document in cursor:
            documents.append(document)
        documents.sort(key=lambda document: document["created_at"], reverse=True)
        return [await self._to_response(document) for document in documents]

    async def register_node_runtime(self, *, operator_address: str, callback_url: str) -> dict[str, str]:
        checksum_address = self.chain_service.web3_client.checksum_address(operator_address)
        record = NodeRuntimeRecord(
            operator_address=checksum_address,
            callback_url=callback_url.rstrip("/"),
        )
        await self.chain_service.refresh_operator_heartbeat(checksum_address)
        await self.database[NODE_RUNTIMES].update_one(
            {"operator_address": checksum_address},
            {
                "$set": {
                    **record.model_dump(),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
        await self._dispatch_pending_tasks_for_node(checksum_address)
        return {
            "status": "registered",
            "operator_address": checksum_address,
            "callback_url": callback_url.rstrip("/"),
        }

    async def list_node_runtimes(self) -> list[dict[str, str]]:
        cursor = self.database[NODE_RUNTIMES].find({})
        runtimes: list[dict[str, str]] = []
        async for document in cursor:
            document.pop("_id", None)
            runtimes.append(
                {
                    "operator_address": document["operator_address"],
                    "callback_url": document["callback_url"],
                }
            )
        runtimes.sort(key=lambda runtime: runtime["operator_address"])
        return runtimes

    async def get_request(self, request_id: str) -> InferenceRequestResponse:
        document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if document is None:
            raise KeyError(f"inference request {request_id} not found")
        return await self._to_response(document)

    async def get_request_status(self, request_id: str) -> InferenceRequestResponse | TextInferenceResult:
        document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if document is None:
            raise KeyError(f"inference request {request_id} not found")
        if document.get("text_mode"):
            return await self._to_text_result(document)
        return await self._to_response(document)

    async def get_request_by_task_id(self, task_id: str) -> InferenceRequestResponse:
        document = await self.database[INFERENCE_REQUESTS].find_one({"task_id": task_id})
        if document is None:
            raise KeyError(f"inference request task {task_id} not found")
        return await self._to_response(document)

    async def get_request_status_by_task_id(self, task_id: str) -> InferenceRequestResponse | TextInferenceResult:
        document = await self.database[INFERENCE_REQUESTS].find_one({"task_id": task_id})
        if document is None:
            raise KeyError(f"inference request task {task_id} not found")
        if document.get("text_mode"):
            return await self._to_text_result(document)
        return await self._to_response(document)

    async def attach_permit(
        self,
        task_id: str,
        payload: InferencePermitAttachmentRequest,
    ) -> dict[str, str]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"task_id": task_id})
        if request_document is None:
            raise KeyError(f"inference request task {task_id} not found")

        assignment_document = await self.database[QUORUM_ASSIGNMENTS].find_one({"task_id": task_id})
        if assignment_document is None:
            raise ValueError("quorum assignment missing for inference request")

        target_node = payload.node or assignment_document["leader_address"]
        serialized_permit = self._serialize_permit(payload.permit)
        current_permit_document = await self.database[PERMITS].find_one({"task_id": task_id})
        current_entries = self._permit_records_from_document(current_permit_document)
        merged_entries = self._merge_permit_entries(
            current_entries,
            [
                PermitEntryRecord(
                    node_address=self.chain_service.web3_client.checksum_address(target_node),
                    permit=serialized_permit,
                    status="shared-permit-provided",
                )
            ],
        )
        await self.database[PERMITS].update_one(
            {"task_id": task_id},
            {
                "$set": PermitRecord(
                    task_id=task_id,
                    permits=merged_entries,
                ).model_dump()
            },
            upsert=True,
        )

        metadata = dict(request_document.get("metadata", {}))
        metadata["permits"] = [self._permit_record_to_metadata(entry) for entry in merged_entries]
        metadata["permit_attached_at"] = datetime.now(timezone.utc).isoformat()
        await self.database[INFERENCE_REQUESTS].update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        await self._dispatch_request_to_quorum(request_document["request_id"], [target_node])

        return {
            "status": "permit_attached",
            "task_id": task_id,
            "leader_address": target_node,
        }

    async def submit_leader_result(
        self,
        request_id: str,
        payload: LeaderResultSubmissionRequest,
    ) -> dict[str, object]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if request_document is None:
            raise KeyError(f"inference request {request_id} not found")

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": request_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        leader_address = self.chain_service.web3_client.checksum_address(payload.leader_address)
        if leader_address != assignment["leader_address"]:
            raise ValueError("leader result submitted by non-leader address")

        result_hash = payload.result_hash or self.chain_service.web3_client.keccak_uint256(payload.risk_score)
        metadata = dict(request_document.get("metadata", {}))
        metadata["leader_submission"] = {
            "leader_address": leader_address,
            "risk_score": payload.risk_score,
            "leader_confidence": payload.leader_confidence,
            "leader_summary": payload.leader_summary,
            "provider": payload.provider,
            "model": payload.model,
            "result_hash": result_hash,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_id},
            {"$set": {"metadata": metadata, "updated_at": datetime.now(timezone.utc)}},
        )

        finalized = await self._attempt_finalize_request(request_id)
        return {
            "status": "leader_result_recorded" if finalized is None else "committed",
            "request_id": request_id,
            "task_id": request_document["task_id"],
            "result_hash": result_hash,
            "finalized": finalized is not None,
        }

    async def submit_internal_task_result(
        self,
        job_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": job_id})
        if request_document is None:
            raise KeyError(f"inference request {job_id} not found")

        if request_document.get("text_mode"):
            text_payload = LeaderTextResultSubmission.model_validate(payload)
            return await self.submit_text_leader_result(text_payload)

        raise ValueError("internal text result endpoint only supports text-mode tasks")

    async def submit_text_leader_result(
        self,
        payload: LeaderTextResultSubmission,
    ) -> dict[str, object]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": payload.job_id})
        if request_document is None:
            raise KeyError(f"inference request {payload.job_id} not found")
        if not request_document.get("text_mode"):
            raise ValueError("task is not a text-mode request")

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": payload.job_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        verdict = payload.verdict.upper() if isinstance(payload.verdict, str) else None
        if verdict not in {None, "CONFIRM", "REJECT"}:
            raise ValueError("leader verdict must be CONFIRM or REJECT")

        metadata = dict(request_document.get("metadata", {}))
        metadata["text_leader_result"] = {
            "leader_address": assignment["leader_address"],
            "output_cid": payload.output_cid,
            "commitment_hash": payload.commitment_hash,
            "encrypted_output_key_high": payload.encrypted_output_key_high,
            "encrypted_output_key_low": payload.encrypted_output_key_low,
            "encrypted_output_key_inputs": payload.encrypted_output_key_inputs,
            "verdict": verdict,
            "confidence": payload.confidence,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        output_key_store_tx = None
        output_key_store_job_id = None
        if payload.encrypted_output_key_inputs:
            output_key_store_job_id = self.chain_service.web3_client.keccak_text(
                f"{request_document['task_id']}:output-key"
            )
            output_key_store = await self.chain_service.store_text_prompt_key(
                task_id=output_key_store_job_id,
                encrypted_high_input=payload.encrypted_output_key_inputs["high"],
                encrypted_low_input=payload.encrypted_output_key_inputs["low"],
                allowed_nodes=[request_document["developer_address"]],
            )
            output_key_store_tx = output_key_store.get("tx_hash")
            metadata["output_key_store_job_id"] = output_key_store_job_id
            metadata["output_key_store_tx"] = output_key_store_tx
            metadata["output_key_store_address"] = self.chain_service.settings.PROMPT_KEY_STORE_ADDRESS

        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": payload.job_id},
            {
                "$set": {
                    "output_cid": payload.output_cid,
                    "commitment_hash": payload.commitment_hash,
                    "encrypted_output_key_high": payload.encrypted_output_key_high,
                    "encrypted_output_key_low": payload.encrypted_output_key_low,
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        finalized = await self._attempt_finalize_text_request(payload.job_id)
        return {
            "status": "leader_result_recorded" if finalized is None else "committed",
            "job_id": payload.job_id,
            "task_id": request_document["task_id"],
            "commitment_hash": payload.commitment_hash,
            "output_key_store_tx": output_key_store_tx,
            "output_key_store_job_id": output_key_store_job_id,
            "finalized": finalized is not None,
        }

    async def submit_verifier_verdict(
        self,
        request_id: str,
        payload: VerifierVerdictSubmissionRequest,
    ) -> dict[str, object]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if request_document is None:
            raise KeyError(f"inference request {request_id} not found")

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": request_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        verifier_address = self.chain_service.web3_client.checksum_address(payload.verifier_address)
        if verifier_address not in assignment["verifier_addresses"]:
            raise ValueError("verifier verdict submitted by non-quorum verifier")

        result_hash = payload.result_hash
        if result_hash is None and payload.risk_score is not None:
            result_hash = self.chain_service.web3_client.keccak_uint256(payload.risk_score)

        verdict_record = VerifierVerdictRecord(
            request_id=request_id,
            task_id=request_document["task_id"],
            verifier_address=verifier_address,
            accepted=payload.accepted,
            confidence=payload.confidence,
            reason=payload.reason,
            result_hash=result_hash,
            risk_score=payload.risk_score,
            provider=payload.provider,
            model=payload.model,
            summary=payload.summary,
            updated_at=datetime.now(timezone.utc),
        )
        await self.database[VERIFIER_VERDICTS].update_one(
            {"request_id": request_id, "verifier_address": verifier_address},
            {"$set": verdict_record.model_dump()},
            upsert=True,
        )

        finalized = await self._attempt_finalize_request(request_id)
        return {
            "status": "verifier_verdict_recorded" if finalized is None else "committed",
            "request_id": request_id,
            "task_id": request_document["task_id"],
            "verifier_address": verifier_address,
            "finalized": finalized is not None,
        }

    async def submit_internal_task_verification(
        self,
        job_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": job_id})
        if request_document is None:
            raise KeyError(f"inference request {job_id} not found")

        if request_document.get("text_mode"):
            text_payload = VerifierTextVerdict.model_validate(payload)
            return await self.submit_text_verifier_verdict(text_payload)

        raise ValueError("internal text verify endpoint only supports text-mode tasks")

    async def submit_text_verifier_verdict(
        self,
        payload: VerifierTextVerdict,
    ) -> dict[str, object]:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": payload.job_id})
        if request_document is None:
            raise KeyError(f"inference request {payload.job_id} not found")
        if not request_document.get("text_mode"):
            raise ValueError("task is not a text-mode request")

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": payload.job_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        verifier_address = self.chain_service.web3_client.checksum_address(payload.verifier_address)
        if verifier_address not in assignment["verifier_addresses"]:
            raise ValueError("verifier verdict submitted by non-quorum verifier")

        verdict = payload.verdict.upper()
        if verdict not in {"CONFIRM", "REJECT"}:
            raise ValueError("verifier verdict must be CONFIRM or REJECT")

        verdict_record = VerifierVerdictRecord(
            request_id=payload.job_id,
            task_id=request_document["task_id"],
            verifier_address=verifier_address,
            accepted=verdict == "CONFIRM",
            confidence=payload.confidence,
            reason=None if verdict == "CONFIRM" else "verifier rejected text commitment",
            result_hash=payload.commitment_hash,
            updated_at=datetime.now(timezone.utc),
        )
        await self.database[VERIFIER_VERDICTS].update_one(
            {"request_id": payload.job_id, "verifier_address": verifier_address},
            {"$set": verdict_record.model_dump()},
            upsert=True,
        )

        finalized = await self._attempt_finalize_text_request(payload.job_id)
        return {
            "status": "verifier_verdict_recorded" if finalized is None else "committed",
            "job_id": payload.job_id,
            "task_id": request_document["task_id"],
            "verifier_address": verifier_address,
            "finalized": finalized is not None,
        }

    async def commit_request(
        self,
        request_id: str,
        payload: InferenceCommitRequest,
    ) -> InferenceCommitResponse:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if request_document is None:
            raise KeyError(f"inference request {request_id} not found")
        if request_document["status"] != "queued":
            raise ValueError("inference request already committed")

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": request_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        result_hash = payload.result_hash or self.chain_service.web3_client.keccak_uint256(payload.risk_score)
        leader_output = json.dumps(
            {
                "task_id": request_document["task_id"],
                "loan_id": request_document.get("loan_id"),
                "risk_score": payload.risk_score,
                "confidence": payload.leader_confidence,
                "provider": payload.provider,
                "model": payload.model,
                "summary": payload.leader_summary,
                "response_hash": result_hash,
            },
            sort_keys=True,
        )
        aggregation = self.verdict_aggregator.aggregate(
            leader_output=leader_output,
            leader_confidence=payload.leader_confidence,
            assigned_verifiers=assignment["verifier_addresses"],
            provided_verdicts=payload.verifier_verdicts,
            result_hash=result_hash,
            rejection_reason=payload.rejection_reason,
        )

        if aggregation["accepted"]:
            chain_result = await self.chain_service.finalize_execution(
                task_id=request_document["task_id"],
                result_hash=str(aggregation["result_hash"]),
                leader=assignment["leader_address"],
                cross_verifier=assignment["verifier_addresses"][0],
                accepted=True,
            )
            new_status = "accepted"
        else:
            chain_result = await self.chain_service.finalize_execution(
                task_id=request_document["task_id"],
                result_hash=str(aggregation["result_hash"]),
                leader=assignment["leader_address"],
                cross_verifier=assignment["verifier_addresses"][0],
                accepted=False,
            )
            new_status = "rejected"

        await self.chain_service.record_quorum_outcome(
            assignment["leader_address"],
            assignment["verifier_addresses"],
            bool(aggregation["accepted"]),
        )

        verdict_records = [
            VerifierVerdictRecord(
                request_id=request_document["request_id"],
                task_id=request_document["task_id"],
                verifier_address=verdict.verifier_address,
                accepted=verdict.accepted,
                confidence=verdict.confidence,
                reason=verdict.reason,
            )
            for verdict in aggregation["verifier_verdicts"]
        ]

        for verdict_record in verdict_records:
            await self.database[VERIFIER_VERDICTS].update_one(
                {
                    "request_id": verdict_record.request_id,
                    "verifier_address": verdict_record.verifier_address,
                },
                {"$set": verdict_record.model_dump()},
                upsert=True,
            )

        certificate = QuorumCertificateRecord(
            request_id=request_document["request_id"],
            task_id=request_document["task_id"],
            model_id=request_document["model_id"],
            leader_address=assignment["leader_address"],
            verifier_addresses=assignment["verifier_addresses"],
            result_hash=str(aggregation["result_hash"]),
            confirm_count=int(aggregation["confirm_count"]),
            reject_count=int(aggregation["reject_count"]),
            aggregated_confidence=int(aggregation["aggregated_confidence"]),
            accepted=bool(aggregation["accepted"]),
            chain_tx_hash=chain_result["tx_hash"],
        )
        await self.database[QUORUM_CERTIFICATES].update_one(
            {"request_id": certificate.request_id},
            {"$set": certificate.model_dump()},
            upsert=True,
        )

        metadata = dict(request_document.get("metadata", {}))
        metadata["result_commit_tx"] = chain_result["tx_hash"]
        if new_status == "accepted":
            metadata["escrow_release_tx"] = chain_result["tx_hash"]
            metadata["escrow_release_mode"] = "mock-visible-same-tx"

        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_document["request_id"]},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc),
                    "metadata": metadata,
                    "result_hash": aggregation["result_hash"],
                    "result_preview": leader_output,
                    "risk_score": payload.risk_score,
                    "chain_tx_hash": chain_result["tx_hash"],
                    "aggregated_confidence": aggregation["aggregated_confidence"],
                    "confirm_count": aggregation["confirm_count"],
                    "reject_count": aggregation["reject_count"],
                }
            },
        )

        return InferenceCommitResponse(
            request_id=request_document["request_id"],
            task_id=request_document["task_id"],
            accepted=bool(aggregation["accepted"]),
            confirm_count=int(aggregation["confirm_count"]),
            reject_count=int(aggregation["reject_count"]),
            aggregated_confidence=int(aggregation["aggregated_confidence"]),
            result_hash=str(aggregation["result_hash"]),
            chain_tx_hash=chain_result["tx_hash"],
        )

    async def _attempt_finalize_request(self, request_id: str) -> InferenceCommitResponse | None:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if request_document is None:
            raise KeyError(f"inference request {request_id} not found")
        if request_document["status"] != "queued":
            return None

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": request_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        metadata = dict(request_document.get("metadata", {}))
        leader_submission = metadata.get("leader_submission")
        if not isinstance(leader_submission, dict):
            return None

        verifier_cursor = self.database[VERIFIER_VERDICTS].find({"request_id": request_id})
        verifier_documents: list[dict] = []
        async for verifier_document in verifier_cursor:
            verifier_document.pop("_id", None)
            verifier_documents.append(verifier_document)

        if len(verifier_documents) < len(assignment["verifier_addresses"]):
            return None

        verdicts_by_address = {
            verdict_document["verifier_address"].lower(): verdict_document
            for verdict_document in verifier_documents
        }
        normalized_verdicts: list[VerifierVerdictInput] = []
        for verifier_address in assignment["verifier_addresses"]:
            verdict_document = verdicts_by_address.get(verifier_address.lower())
            if verdict_document is None:
                return None
            accepted = verdict_document.get("accepted")
            if accepted is None:
                accepted = verdict_document.get("result_hash") == leader_submission["result_hash"]
            reason = verdict_document.get("reason")
            if not accepted and not reason:
                reason = "verifier result hash did not match leader result hash"
            normalized_verdicts.append(
                VerifierVerdictInput(
                    verifier_address=verifier_address,
                    accepted=bool(accepted),
                    confidence=int(verdict_document.get("confidence", leader_submission["leader_confidence"])),
                    reason=reason,
                )
            )

        return await self.commit_request(
            request_id,
            InferenceCommitRequest(
                risk_score=int(leader_submission["risk_score"]),
                leader_confidence=int(leader_submission["leader_confidence"]),
                leader_summary=leader_submission.get("leader_summary"),
                provider=leader_submission.get("provider"),
                model=leader_submission.get("model"),
                result_hash=str(leader_submission["result_hash"]),
                verifier_verdicts=normalized_verdicts,
            ),
        )

    async def _attempt_finalize_text_request(self, request_id: str) -> TextInferenceResult | None:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if request_document is None:
            raise KeyError(f"inference request {request_id} not found")
        if not request_document.get("text_mode"):
            return None
        if request_document.get("status") != "queued":
            return await self._to_text_result(request_document)

        assignment = await self.database[QUORUM_ASSIGNMENTS].find_one({"request_id": request_id})
        if assignment is None:
            raise ValueError("quorum assignment missing for inference request")

        metadata = dict(request_document.get("metadata", {}))
        leader_result = metadata.get("text_leader_result")
        if not isinstance(leader_result, dict):
            return None

        leader_hash = leader_result.get("commitment_hash")
        if not isinstance(leader_hash, str) or not leader_hash:
            raise ValueError("text leader result missing commitment hash")

        verifier_cursor = self.database[VERIFIER_VERDICTS].find({"request_id": request_id})
        verifier_documents: list[dict] = []
        async for verifier_document in verifier_cursor:
            verifier_document.pop("_id", None)
            verifier_documents.append(verifier_document)

        total_nodes = 1 + len(assignment["verifier_addresses"])
        required_confirmations = self._required_text_confirmations(total_nodes)

        hash_counts: dict[str, int] = {leader_hash: 1}
        confidence_total = int(leader_result.get("confidence") or 0)
        matched_confidence_count = 1 if leader_result.get("confidence") is not None else 0

        for verifier_document in verifier_documents:
            commitment_hash = verifier_document.get("result_hash")
            if not isinstance(commitment_hash, str) or not commitment_hash:
                continue
            hash_counts[commitment_hash] = hash_counts.get(commitment_hash, 0) + 1
            if commitment_hash == leader_hash and verifier_document.get("confidence") is not None:
                confidence_total += int(verifier_document["confidence"])
                matched_confidence_count += 1

        winning_hash, winning_count = max(hash_counts.items(), key=lambda item: item[1])

        if winning_count >= required_confirmations:
            aggregated_confidence = (
                int(confidence_total / matched_confidence_count)
                if winning_hash == leader_hash and matched_confidence_count > 0
                else int(request_document.get("aggregated_confidence") or 0)
            )
            await self.database[INFERENCE_REQUESTS].update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "accepted",
                        "commitment_hash": winning_hash,
                        "updated_at": datetime.now(timezone.utc),
                        "aggregated_confidence": aggregated_confidence,
                        "confirm_count": winning_count,
                        "reject_count": max(0, total_nodes - winning_count),
                    }
                },
            )
            refreshed = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
            return await self._to_text_result(refreshed)

        if len(verifier_documents) >= len(assignment["verifier_addresses"]):
            await self.database[INFERENCE_REQUESTS].update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "rejected",
                        "updated_at": datetime.now(timezone.utc),
                        "confirm_count": winning_count,
                        "reject_count": max(0, total_nodes - winning_count),
                    }
                },
            )
            refreshed = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
            return await self._to_text_result(refreshed)

        return None

    async def submit_dispute(
        self,
        request_id: str,
        payload: DisputeSubmissionRequest,
    ) -> dict:
        request_document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if request_document is None:
            raise KeyError(f"inference request {request_id} not found")
        record = DisputeRecord(
            request_id=request_id,
            task_id=request_document["task_id"],
            developer_address=payload.developer_address,
            evidence_hash=payload.evidence_hash,
            evidence_uri=payload.evidence_uri,
            notes=payload.notes,
        )
        await self.database[DISPUTES].update_one(
            {"request_id": request_id},
            {"$set": record.model_dump()},
            upsert=True,
        )
        metadata = dict(request_document.get("metadata", {}))
        dispute_submission_tx = self.chain_service.web3_client.ensure_hex_prefix(
            self.chain_service.web3_client.keccak_text(
                f"mock-dispute-submit:{request_document['task_id']}:{payload.evidence_hash}"
            )
        )
        dispute_resolution_tx = self.chain_service.web3_client.ensure_hex_prefix(
            self.chain_service.web3_client.keccak_text(
                f"mock-dispute-resolve:{request_document['task_id']}:{payload.evidence_hash}"
            )
        )
        metadata["dispute_submission_tx"] = dispute_submission_tx
        metadata["dispute_resolution_tx"] = dispute_resolution_tx
        metadata["dispute_resolution_mode"] = "mock-visible-demo"
        metadata["dispute_opened_at"] = datetime.now(timezone.utc).isoformat()
        if request_document.get("coverage_type") and not metadata.get("escrow_release_tx"):
            metadata["escrow_release_tx"] = dispute_resolution_tx
        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": "disputed",
                    "updated_at": datetime.now(timezone.utc),
                    "metadata": metadata,
                }
            },
        )
        return record.model_dump()

    async def get_dispute(self, request_id: str) -> dict | None:
        document = await self.database[DISPUTES].find_one({"request_id": request_id})
        if document is None:
            return None
        document.pop("_id", None)
        return document

    async def _to_response(self, request_document: dict) -> InferenceRequestResponse:
        request_document = dict(request_document)
        request_document.pop("_id", None)

        assignment_document = await self.database[QUORUM_ASSIGNMENTS].find_one(
            {"request_id": request_document["request_id"]}
        )
        if assignment_document is None:
            raise ValueError("missing quorum assignment")
        assignment_document.pop("_id", None)

        metadata = dict(request_document.get("metadata", {}))
        raw_text_request = metadata.get("text_request")
        text_request: TextInferenceRequest | None = None
        if isinstance(raw_text_request, dict):
            text_request = TextInferenceRequest.model_validate(raw_text_request)
        raw_leader_submission = metadata.get("leader_submission")
        leader_submission: LeaderSubmissionResponse | None = None
        if isinstance(raw_leader_submission, dict):
            submitted_at = raw_leader_submission.get("submitted_at")
            leader_submission = LeaderSubmissionResponse(
                leader_address=raw_leader_submission.get("leader_address", assignment_document["leader_address"]),
                risk_score=raw_leader_submission.get("risk_score"),
                confidence=raw_leader_submission.get("leader_confidence"),
                summary=raw_leader_submission.get("leader_summary"),
                provider=raw_leader_submission.get("provider"),
                model=raw_leader_submission.get("model"),
                result_hash=raw_leader_submission.get("result_hash"),
                submitted_at=datetime.fromisoformat(submitted_at) if isinstance(submitted_at, str) else None,
            )

        verifier_cursor = self.database[VERIFIER_VERDICTS].find({"request_id": request_document["request_id"]})
        verifier_documents: list[dict] = []
        async for verifier_document in verifier_cursor:
            verifier_document.pop("_id", None)
            verifier_documents.append(verifier_document)
        verdicts_by_address = {
            str(verdict_document["verifier_address"]).lower(): verdict_document
            for verdict_document in verifier_documents
        }
        verifier_verdicts: list[VerifierVerdictResponse] = []
        for verifier_address in assignment_document["verifier_addresses"]:
            verdict_document = verdicts_by_address.get(verifier_address.lower())
            if verdict_document is None:
                verifier_verdicts.append(
                    VerifierVerdictResponse(
                        verifier_address=verifier_address,
                        submitted=False,
                    )
                )
                continue
            verifier_verdicts.append(
                VerifierVerdictResponse(
                    verifier_address=verifier_address,
                    submitted=True,
                    accepted=verdict_document.get("accepted"),
                    confidence=verdict_document.get("confidence"),
                    reason=verdict_document.get("reason"),
                    risk_score=verdict_document.get("risk_score"),
                    result_hash=verdict_document.get("result_hash"),
                    provider=verdict_document.get("provider"),
                    model=verdict_document.get("model"),
                    summary=verdict_document.get("summary"),
                    updated_at=verdict_document.get("updated_at"),
                )
            )

        return InferenceRequestResponse(
            job_id=request_document["request_id"],
            request_id=request_document["request_id"],
            task_id=request_document["task_id"],
            leader_address=assignment_document["leader_address"],
            developer_address=request_document["developer_address"],
            model_id=request_document["model_id"],
            mode=request_document.get("mode", "risk"),
            text_request=text_request,
            text_mode=bool(request_document.get("text_mode", False)),
            encrypted_features=[
                EncryptedFeatureResponse(
                    ct_hash=feature["ctHash"],
                    utype=feature["utype"],
                    signature=feature["signature"],
                )
                for feature in request_document["encrypted_features"]
            ],
            feature_types=request_document["feature_types"],
            loan_id=request_document.get("loan_id"),
            coverage_type=request_document.get("coverage_type"),
            max_fee_gnk=request_document.get("max_fee_gnk", 0),
            status=request_document["status"],
            min_tier=request_document["min_tier"],
            zdr_required=request_document["zdr_required"],
            verifier_count=request_document["verifier_count"],
            quorum=QuorumAssignmentResponse(
                leader_address=assignment_document["leader_address"],
                verifier_addresses=assignment_document["verifier_addresses"],
                candidate_addresses=assignment_document["candidate_addresses"],
            ),
            metadata=metadata,
            prompt_cid=request_document.get("prompt_cid"),
            encrypted_prompt_key_high=request_document.get("encrypted_prompt_key_high"),
            encrypted_prompt_key_low=request_document.get("encrypted_prompt_key_low"),
            encrypted_output_key_high=request_document.get("encrypted_output_key_high"),
            encrypted_output_key_low=request_document.get("encrypted_output_key_low"),
            output_cid=request_document.get("output_cid"),
            commitment_hash=request_document.get("commitment_hash"),
            result_hash=request_document.get("result_hash"),
            result_preview=request_document.get("result_preview"),
            risk_score=request_document.get("risk_score"),
            leader_submission=leader_submission,
            verifier_verdicts=verifier_verdicts,
            chain_tx_hash=request_document.get("chain_tx_hash"),
            aggregated_confidence=request_document.get("aggregated_confidence"),
            confirm_count=request_document.get("confirm_count", 0),
            reject_count=request_document.get("reject_count", 0),
            created_at=request_document["created_at"],
            updated_at=request_document["updated_at"],
        )

    async def _to_text_result(self, request_document: dict) -> TextInferenceResult:
        request_document = dict(request_document)
        request_document.pop("_id", None)

        assignment_document = await self.database[QUORUM_ASSIGNMENTS].find_one(
            {"request_id": request_document["request_id"]}
        )
        if assignment_document is None:
            raise ValueError("missing quorum assignment")
        assignment_document.pop("_id", None)

        status_map = {
            "queued": "QUEUED",
            "accepted": "ACCEPTED",
            "rejected": "REJECTED",
            "disputed": "DISPUTED",
            "timedout": "TIMEDOUT",
        }
        status = status_map.get(str(request_document.get("status", "queued")).lower(), "QUEUED")

        dispute_deadline = request_document.get("dispute_deadline")
        if isinstance(dispute_deadline, datetime):
            dispute_deadline_unix = int(dispute_deadline.timestamp())
        else:
            dispute_deadline_unix = None

        quorum: QuorumCertificate | None = None
        if assignment_document.get("verifier_addresses"):
            quorum = QuorumCertificate(
                verifier_addresses=list(assignment_document["verifier_addresses"]),
                confirmations=int(request_document.get("confirm_count", 0)),
                confidence=int(request_document.get("aggregated_confidence") or 0),
            )

        return TextInferenceResult(
            job_id=request_document["request_id"],
            status=status,
            output_cid=request_document.get("output_cid"),
            commitment_hash=request_document.get("commitment_hash"),
            encrypted_output_key_high=request_document.get("encrypted_output_key_high"),
            encrypted_output_key_low=request_document.get("encrypted_output_key_low"),
            quorum=quorum,
            dispute_deadline=dispute_deadline_unix,
        )

    def _required_text_confirmations(self, total_nodes: int) -> int:
        return (2 * total_nodes + 2) // 3

    async def _dispatch_request_to_quorum(
        self,
        request_id: str,
        target_nodes: list[str] | None = None,
    ) -> None:
        response = await self.get_request(request_id)
        request_payload = response.model_dump(mode="json")
        leader_address = response.quorum.leader_address
        verifier_addresses = list(response.quorum.verifier_addresses)

        desired_nodes = {
            self.chain_service.web3_client.checksum_address(address)
            for address in (target_nodes or [leader_address, *verifier_addresses])
        }
        runtime_map = await self._get_runtime_map()

        for node_address in desired_nodes:
            callback_url = runtime_map.get(node_address)
            if not callback_url:
                logger.warning(
                    "No runtime callback registered for operator=%s request_id=%s",
                    node_address,
                    request_id,
                )
                continue

            role = "leader" if node_address == leader_address else "verifier"
            if role == "leader" and response.leader_submission is not None:
                continue

            if role == "verifier":
                matching_verdict = next(
                    (
                        verdict
                        for verdict in response.verifier_verdicts
                        if verdict.verifier_address.lower() == node_address.lower()
                    ),
                    None,
                )
                if matching_verdict and matching_verdict.submitted:
                    continue

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    push_response = await client.post(
                        f"{callback_url}/internal/task",
                        json={
                            "role": role,
                            "request": request_payload,
                        },
                    )
                    push_response.raise_for_status()
                logger.info(
                    "Dispatched request_id=%s task_id=%s role=%s to operator=%s callback=%s",
                    response.request_id,
                    response.task_id,
                    role,
                    node_address,
                    callback_url,
                )
            except Exception:
                logger.exception(
                    "Failed to dispatch request_id=%s role=%s to operator=%s callback=%s",
                    response.request_id,
                    role,
                    node_address,
                    callback_url,
                )

    async def _dispatch_pending_tasks_for_node(self, operator_address: str) -> None:
        checksum_address = self.chain_service.web3_client.checksum_address(operator_address)
        cursor = self.database[INFERENCE_REQUESTS].find({"status": "queued"})
        async for document in cursor:
            if (
                document.get("leader_address") == checksum_address
                or checksum_address in document.get("verifier_addresses", [])
            ):
                await self._dispatch_request_to_quorum(document["request_id"], [checksum_address])

    async def _get_runtime_map(self) -> dict[str, str]:
        runtime_map: dict[str, str] = {}
        cursor = self.database[NODE_RUNTIMES].find({})
        async for document in cursor:
            runtime_map[self.chain_service.web3_client.checksum_address(document["operator_address"])] = document[
                "callback_url"
            ]
        return runtime_map

    def _serialize_permit(self, permit: str | dict) -> str:
        if isinstance(permit, str):
            return permit
        return json.dumps(permit, sort_keys=True)

    def _resolve_text_prompt_key_inputs(
        self,
        metadata: dict[str, Any],
        *,
        fallback_high_handle: str | None = None,
        fallback_low_handle: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        raw_inputs = metadata.get("cofhe_prompt_key_inputs")
        if not isinstance(raw_inputs, dict):
            if self.chain_service.settings.MOCK_CHAIN and fallback_high_handle and fallback_low_handle:
                return {
                    "high": {"ctHash": fallback_high_handle, "securityZone": 0, "utype": 8, "signature": "0x"},
                    "low": {"ctHash": fallback_low_handle, "securityZone": 0, "utype": 8, "signature": "0x"},
                }
            raise ValueError(
                "Text jobs require metadata.cofhe_prompt_key_inputs.high/low so the ICL can store prompt keys on-chain"
            )

        high_input = raw_inputs.get("high")
        low_input = raw_inputs.get("low")
        if not isinstance(high_input, dict) or not isinstance(low_input, dict):
            raise ValueError(
                "Text jobs require metadata.cofhe_prompt_key_inputs.high and .low objects"
            )
        return {"high": high_input, "low": low_input}

    def _normalize_permit_entries(self, permits: list) -> list[PermitEntryRecord]:
        normalized_entries: list[PermitEntryRecord] = []
        for permit_entry in permits:
            normalized_entries.append(
                PermitEntryRecord(
                    node_address=self.chain_service.web3_client.checksum_address(permit_entry.node),
                    permit=self._serialize_permit(permit_entry.permit),
                    status="shared-permit-provided",
                )
            )
        return normalized_entries

    def _merge_permit_entries(
        self,
        current_entries: list[PermitEntryRecord],
        new_entries: list[PermitEntryRecord],
    ) -> list[PermitEntryRecord]:
        merged = {entry.node_address: entry for entry in current_entries}
        for entry in new_entries:
            merged[entry.node_address] = entry
        return list(merged.values())

    def _permit_records_from_document(self, permit_document: dict | None) -> list[PermitEntryRecord]:
        if not permit_document:
            return []
        return [
            PermitEntryRecord(**entry)
            for entry in permit_document.get("permits", [])
        ]

    def _permit_record_to_metadata(self, permit_record: PermitEntryRecord) -> dict[str, str]:
        return {
            "node_address": permit_record.node_address,
            "permit": permit_record.permit,
            "status": permit_record.status,
        }

    def _resolve_requested_quorum(
        self,
        payload: InferenceRequestCreate,
        selected_quorum: dict[str, list[str] | str],
    ) -> dict[str, list[str] | str]:
        if not payload.leader_address and not payload.verifier_addresses:
            return selected_quorum

        if not payload.leader_address:
            raise ValueError("leader_address is required when overriding quorum selection")
        if len(payload.verifier_addresses) != payload.verifier_count:
            raise ValueError(
                f"verifier_addresses must contain exactly {payload.verifier_count} addresses"
            )

        leader_address = self.chain_service.web3_client.checksum_address(payload.leader_address)
        verifier_addresses = [
            self.chain_service.web3_client.checksum_address(address)
            for address in payload.verifier_addresses
        ]
        if leader_address in verifier_addresses:
            raise ValueError("leader_address cannot also appear in verifier_addresses")

        candidate_addresses = [
            self.chain_service.web3_client.checksum_address(address)
            for address in list(selected_quorum["candidate_addresses"])
        ]
        missing_addresses = [
            address
            for address in [leader_address, *verifier_addresses]
            if address not in candidate_addresses
        ]
        if missing_addresses:
            raise ValueError(
                "requested quorum contains inactive or unavailable nodes: "
                + ", ".join(missing_addresses)
            )

        return {
            "leader_address": leader_address,
            "verifier_addresses": verifier_addresses,
            "candidate_addresses": candidate_addresses,
        }
