import { apiClient } from './client'

export type InferenceRequestPayload = {
  developer_address: string
  model_id: string
  encrypted_input: Array<{
    ctHash: string
    utype: string | number
    signature: string
  }>
  permits: Array<{
    node: string
    permit: Record<string, unknown> | string
  }>
  leader_address: string
  verifier_addresses: string[]
  feature_types: string[]
  loan_id: string
  coverage_type: string | null
  max_fee_gnk: number
  min_tier: number
  zdr_required: boolean
  verifier_count: number
  metadata: Record<string, unknown>
}

export type BackendInferenceRequest = {
  request_id: string
  task_id: string
  leader_address: string | null
  developer_address: string
  model_id: string
  encrypted_features: Array<{
    ct_hash: string
    utype: string | number
    signature: string
  }>
  feature_types: string[]
  loan_id: string | null
  coverage_type: string | null
  max_fee_gnk: number
  status: 'queued' | 'accepted' | 'rejected' | 'disputed'
  min_tier: number
  zdr_required: boolean
  verifier_count: number
  quorum: {
    leader_address: string
    verifier_addresses: string[]
    candidate_addresses: string[]
  }
  metadata: Record<string, unknown>
  result_hash: string | null
  result_preview: string | null
  risk_score: number | null
  leader_submission: {
    leader_address: string
    risk_score: number | null
    confidence: number | null
    summary: string | null
    provider: string | null
    model: string | null
    result_hash: string | null
    submitted_at: string | null
  } | null
  verifier_verdicts: Array<{
    verifier_address: string
    submitted: boolean
    accepted: boolean | null
    confidence: number | null
    reason: string | null
    risk_score: number | null
    result_hash: string | null
    provider: string | null
    model: string | null
    summary: string | null
    updated_at: string | null
  }>
  chain_tx_hash: string | null
  aggregated_confidence: number | null
  confirm_count: number
  reject_count: number
  created_at: string
  updated_at: string
}

export type CoverageQuote = {
  request_id: string
  coverage_available: boolean
  recommendation: string
}

export type QuorumPreviewResponse = {
  leader: string
  verifiers: string[]
  candidates: string[]
}

export const inferenceApi = {
  getQuorumPreview(params: { model_id: string; min_tier: number; verifier_count: number; zdr_required?: boolean }) {
    return apiClient.get<QuorumPreviewResponse>('/v1/inference/quorum-preview', { params })
  },
  submit(payload: InferenceRequestPayload) {
    return apiClient.post<BackendInferenceRequest>('/v1/inference/requests', payload)
  },
  getStatus(requestId: string) {
    return apiClient.get<BackendInferenceRequest>(`/v1/inference/${requestId}`)
  },
  list() {
    return apiClient.get<BackendInferenceRequest[]>('/v1/inference')
  },
}

export const coverageApi = {
  quote(requestId: string) {
    return apiClient.get<CoverageQuote>(`/v1/coverage/${requestId}`)
  },
  fileDispute(requestId: string, payload: { developer_address: string; evidence_hash: string; evidence_uri: string; notes: string }) {
    return apiClient.post(`/v1/disputes/${requestId}`, payload)
  },
}
