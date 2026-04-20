from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from db.collections import (
    DISPUTES,
    INFERENCE_REQUESTS,
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
    VerifierVerdictRecord,
)
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
from services.chain_service import ChainService
from services.node_selector import NodeSelector
from services.verdict_aggregator import VerdictAggregator


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
        quorum = await self.preview_quorum(
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
        )
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
            or self.chain_service.web3_client.keccak_text(f"mock-escrow-create:{request_record.task_id}")
        )
        if payload.coverage_type:
            metadata["coverage_id"] = metadata.get("coverage_id") or f"cov_{request_record.request_id[:10]}"
            metadata["coverage_purchase_tx"] = (
                registration_tx_hash
                or self.chain_service.web3_client.keccak_text(f"mock-coverage-purchase:{request_record.task_id}")
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
        return await self.get_request(request_record.request_id)

    async def list_requests(self) -> list[InferenceRequestResponse]:
        cursor = self.database[INFERENCE_REQUESTS].find({})
        documents: list[dict] = []
        async for document in cursor:
            documents.append(document)
        documents.sort(key=lambda document: document["created_at"], reverse=True)
        return [await self._to_response(document) for document in documents]

    async def get_request(self, request_id: str) -> InferenceRequestResponse:
        document = await self.database[INFERENCE_REQUESTS].find_one({"request_id": request_id})
        if document is None:
            raise KeyError(f"inference request {request_id} not found")
        return await self._to_response(document)

    async def get_request_by_task_id(self, task_id: str) -> InferenceRequestResponse:
        document = await self.database[INFERENCE_REQUESTS].find_one({"task_id": task_id})
        if document is None:
            raise KeyError(f"inference request task {task_id} not found")
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
        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_id},
            {"$set": {"status": "disputed", "updated_at": datetime.now(timezone.utc)}},
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
            request_id=request_document["request_id"],
            task_id=request_document["task_id"],
            leader_address=assignment_document["leader_address"],
            developer_address=request_document["developer_address"],
            model_id=request_document["model_id"],
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

    def _serialize_permit(self, permit: str | dict) -> str:
        if isinstance(permit, str):
            return permit
        return json.dumps(permit, sort_keys=True)

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
