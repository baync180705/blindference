import { useEffect, useState } from 'react'

import {
  coverageApi,
  inferenceApi,
  type BackendInferenceRequest,
  type BackendInferenceStatusResponse,
  type BackendTextInferenceStatus,
} from '../api/inferenceApi'

export type DemoStatus = {
  request_id: string
  task_id: string
  mode: 'risk' | 'text'
  status: 'QUEUED' | 'ASSIGNED' | 'EXECUTING' | 'VERIFYING' | 'ACCEPTED' | 'REJECTED' | 'DISPUTED'
  result?: {
    risk_score: number
    confidence: number
    execution_time_ms: number
  }
  text_result?: {
    output_cid?: string
    commitment_hash?: string
    encrypted_output_key_high?: string
    encrypted_output_key_low?: string
  }
  quorum: {
    leader: {
      address: string
      status: string
      reputationScore?: number
      stake?: number
    } | null
    verifiers: Array<{
      address: string
      verdict: 'CONFIRM' | 'REJECT' | null
      confidence: number
      reputationScore?: number
      stake?: number
    }>
    confirm_count: number
    reject_count: number
  }
  coverage_id?: string
  coverage_recommendation?: string
  result_commit_tx?: string
  escrow_creation_tx?: string
  escrow_release_tx?: string
  coverage_purchase_tx?: string
  dispute_submission_tx?: string
  dispute_resolution_tx?: string
  timestamps: Record<string, number>
  developer_address: string
  raw: BackendInferenceStatusResponse
}

function hashLike(value: string | null | undefined) {
  return typeof value === 'string' && value.startsWith('0x') ? value : undefined
}

function toMillis(value: string | number | null | undefined): number | undefined {
  if (typeof value === 'number') return value
  if (typeof value !== 'string' || !value) return undefined
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? undefined : parsed
}

function deriveStage(request: BackendInferenceRequest): DemoStatus['status'] {
  if (request.status === 'accepted') return 'ACCEPTED'
  if (request.status === 'rejected') return 'REJECTED'
  if (request.status === 'disputed') return 'DISPUTED'

  const verifierSubmissions = request.verifier_verdicts.filter((verdict) => verdict.submitted).length
  if (request.leader_submission && verifierSubmissions < request.quorum.verifier_addresses.length) {
    return 'VERIFYING'
  }

  const permits = Array.isArray(request.metadata.permits) ? request.metadata.permits.length : 0
  if (permits >= request.quorum.verifier_addresses.length + 1) {
    return 'EXECUTING'
  }

  return 'ASSIGNED'
}

function isTextStatusResponse(request: BackendInferenceStatusResponse): request is BackendTextInferenceStatus {
  return !('request_id' in request)
}

function buildTimestamps(request: BackendInferenceRequest): Record<string, number> {
  const timestamps: Record<string, number> = {}
  const createdAt = toMillis(request.created_at)
  if (createdAt) {
    timestamps.QUEUED = createdAt
    timestamps.ASSIGNED = createdAt
  }

  const permitAttachedAt = toMillis(
    typeof request.metadata.permit_attached_at === 'string' ? request.metadata.permit_attached_at : undefined,
  )
  if (permitAttachedAt) timestamps.EXECUTING = permitAttachedAt

  const leaderSubmittedAt = toMillis(request.leader_submission?.submitted_at)
  if (leaderSubmittedAt) timestamps.VERIFYING = leaderSubmittedAt

  const finishedAt = toMillis(request.updated_at)
  if (finishedAt) {
    if (request.status === 'accepted') timestamps.ACCEPTED = finishedAt
    if (request.status === 'rejected') timestamps.REJECTED = finishedAt
    if (request.status === 'disputed') timestamps.DISPUTED = finishedAt
  }

  return timestamps
}

function mapRequestToStatus(request: BackendInferenceRequest, coverageRecommendation?: string): DemoStatus {
  const stage = deriveStage(request)
  const metadata = request.metadata ?? {}
  const coverageId = typeof metadata.coverage_id === 'string' ? metadata.coverage_id : undefined

  return {
    request_id: request.request_id,
    task_id: request.task_id,
    mode: request.mode === 'text' || request.text_mode ? 'text' : 'risk',
    status: stage,
    result:
      request.leader_submission || request.result_preview || request.risk_score !== null
        ? {
            risk_score: request.risk_score ?? request.leader_submission?.risk_score ?? 0,
            confidence:
              request.aggregated_confidence ??
              request.leader_submission?.confidence ??
              0,
            execution_time_ms: 1240,
          }
        : undefined,
    text_result:
      request.mode === 'text' || request.text_mode
        ? {
            output_cid: request.output_cid ?? undefined,
            commitment_hash: request.commitment_hash ?? undefined,
            encrypted_output_key_high: request.encrypted_output_key_high ?? undefined,
            encrypted_output_key_low: request.encrypted_output_key_low ?? undefined,
          }
        : undefined,
    quorum: {
      leader: request.quorum?.leader_address
        ? {
            address: request.quorum.leader_address,
            status: request.leader_submission ? 'COMPLETE' : stage === 'EXECUTING' || stage === 'VERIFYING' ? 'EXECUTING' : 'ASSIGNED',
          }
        : null,
      verifiers: request.quorum.verifier_addresses.map((address) => {
        const verdict = request.verifier_verdicts.find(
          (entry) => entry.verifier_address.toLowerCase() === address.toLowerCase(),
        )
        return {
          address,
          verdict: verdict?.submitted ? (verdict.accepted === false ? 'REJECT' : 'CONFIRM') : null,
          confidence: verdict?.confidence ?? 0,
        }
      }),
      confirm_count: request.confirm_count,
      reject_count: request.reject_count,
    },
    coverage_id: coverageId,
    coverage_recommendation: coverageRecommendation,
    result_commit_tx: hashLike(request.chain_tx_hash),
    escrow_creation_tx:
      hashLike(typeof metadata.escrow_creation_tx === 'string' ? metadata.escrow_creation_tx : undefined) ??
      hashLike(typeof metadata.task_registered_tx === 'string' ? metadata.task_registered_tx : undefined),
    escrow_release_tx:
      hashLike(typeof metadata.escrow_release_tx === 'string' ? metadata.escrow_release_tx : undefined) ??
      (request.status === 'accepted' ? hashLike(request.chain_tx_hash) : undefined),
    coverage_purchase_tx: hashLike(
      typeof metadata.coverage_purchase_tx === 'string' ? metadata.coverage_purchase_tx : undefined,
    ),
    dispute_submission_tx: hashLike(
      typeof metadata.dispute_submission_tx === 'string' ? metadata.dispute_submission_tx : undefined,
    ),
    dispute_resolution_tx: hashLike(
      typeof metadata.dispute_resolution_tx === 'string' ? metadata.dispute_resolution_tx : undefined,
    ),
    timestamps: buildTimestamps(request),
    developer_address: request.developer_address,
    raw: request,
  }
}

function mapTextStatusToDemoStatus(
  requestId: string,
  request: BackendTextInferenceStatus,
): DemoStatus {
  const stage =
    request.status === 'TIMEDOUT'
      ? 'REJECTED'
      : request.status

  return {
    request_id: request.job_id || requestId,
    task_id: request.job_id || requestId,
    mode: 'text',
    status: stage,
    text_result: {
      output_cid: request.output_cid ?? undefined,
      commitment_hash: request.commitment_hash ?? undefined,
      encrypted_output_key_high: request.encrypted_output_key_high ?? undefined,
      encrypted_output_key_low: request.encrypted_output_key_low ?? undefined,
    },
    quorum: {
      leader: null,
      verifiers: (request.quorum?.verifier_addresses ?? []).map((address) => ({
        address,
        verdict: request.status === 'ACCEPTED' ? 'CONFIRM' : null,
        confidence: request.quorum?.confidence ?? 0,
      })),
      confirm_count: request.quorum?.confirmations ?? 0,
      reject_count: 0,
    },
    coverage_id: undefined,
    coverage_recommendation: undefined,
    result_commit_tx: undefined,
    escrow_creation_tx: undefined,
    escrow_release_tx: undefined,
    coverage_purchase_tx: undefined,
    dispute_submission_tx: undefined,
    dispute_resolution_tx: undefined,
    timestamps: {},
    developer_address: '',
    raw: request,
  }
}

export function useInferenceStatus(requestId: string) {
  const [status, setStatus] = useState<DemoStatus | null>(null)

  useEffect(() => {
    if (!requestId) return

    let mounted = true
    const poll = async () => {
      try {
        const [requestResponse, coverageResponse] = await Promise.all([
          inferenceApi.getStatus(requestId),
          coverageApi.quote(requestId).catch(() => null),
        ])

        if (!mounted) return

        setStatus(
          isTextStatusResponse(requestResponse.data)
            ? mapTextStatusToDemoStatus(requestId, requestResponse.data)
            : mapRequestToStatus(
                requestResponse.data,
                coverageResponse?.data.recommendation,
              ),
        )
      } catch (error) {
        console.error('Error polling status:', error)
      }
    }

    void poll()
    const interval = window.setInterval(() => {
      void poll()
    }, 3000)

    return () => {
      mounted = false
      window.clearInterval(interval)
    }
  }, [requestId])

  return status
}
