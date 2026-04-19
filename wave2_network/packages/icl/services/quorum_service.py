from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db.collections import (
    DISPUTES,
    INFERENCE_REQUESTS,
    QUORUM_ASSIGNMENTS,
    QUORUM_CERTIFICATES,
    VERIFIER_VERDICTS,
)
from models.db_models import (
    DisputeRecord,
    InferenceRequestRecord,
    QuorumAssignmentRecord,
    QuorumCertificateRecord,
    VerifierVerdictRecord,
)
from models.request_models import (
    DisputeSubmissionRequest,
    InferenceCommitRequest,
    InferenceRequestCreate,
)
from models.response_models import (
    InferenceCommitResponse,
    InferenceRequestResponse,
    QuorumAssignmentResponse,
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

    async def create_request(self, payload: InferenceRequestCreate) -> InferenceRequestResponse:
        quorum = await self.node_selector.select_quorum(
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
        )
        now = datetime.now(timezone.utc)
        task_id = self.chain_service.web3_client.keccak_text(
            f"{payload.developer_address}:{payload.model_id}:{payload.prompt}:{now.isoformat()}"
        )

        request_record = InferenceRequestRecord(
            task_id=task_id,
            invocation_id=self.chain_service.web3_client.task_id_to_invocation_id(task_id),
            developer_address=self.chain_service.web3_client.checksum_address(payload.developer_address),
            model_id=payload.model_id,
            prompt=payload.prompt,
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            verifier_count=payload.verifier_count,
            leader_address=quorum["leader_address"],
            verifier_addresses=list(quorum["verifier_addresses"]),
            metadata=payload.metadata,
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
        await self.chain_service.register_task(
            task_id=request_record.task_id,
            developer_address=request_record.developer_address,
            leader_address=assignment_record.leader_address,
            cross_verifier_address=assignment_record.verifier_addresses[0],
            model_id=request_record.model_id,
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

        result_hash = payload.result_hash or self.chain_service.web3_client.keccak_text(payload.leader_output)
        aggregation = self.verdict_aggregator.aggregate(
            leader_output=payload.leader_output,
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

        await self.database[INFERENCE_REQUESTS].update_one(
            {"request_id": request_document["request_id"]},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc),
                    "result_hash": aggregation["result_hash"],
                    "result_preview": payload.leader_output[:240],
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

        return InferenceRequestResponse(
            request_id=request_document["request_id"],
            task_id=request_document["task_id"],
            developer_address=request_document["developer_address"],
            model_id=request_document["model_id"],
            prompt=request_document["prompt"],
            status=request_document["status"],
            min_tier=request_document["min_tier"],
            zdr_required=request_document["zdr_required"],
            verifier_count=request_document["verifier_count"],
            quorum=QuorumAssignmentResponse(
                leader_address=assignment_document["leader_address"],
                verifier_addresses=assignment_document["verifier_addresses"],
                candidate_addresses=assignment_document["candidate_addresses"],
            ),
            metadata=request_document.get("metadata", {}),
            result_hash=request_document.get("result_hash"),
            result_preview=request_document.get("result_preview"),
            chain_tx_hash=request_document.get("chain_tx_hash"),
            aggregated_confidence=request_document.get("aggregated_confidence"),
            confirm_count=request_document.get("confirm_count", 0),
            reject_count=request_document.get("reject_count", 0),
            created_at=request_document["created_at"],
            updated_at=request_document["updated_at"],
        )
