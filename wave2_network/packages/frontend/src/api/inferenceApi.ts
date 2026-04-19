import { apiClient } from './client'

export type InferenceRequestRecord = {
  request_id: string
  task_id: string
  developer_address: string
  model_id: string
  prompt: string
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
  chain_tx_hash: string | null
  aggregated_confidence: number | null
  confirm_count: number
  reject_count: number
  created_at: string
  updated_at: string
}

export type CreateInferencePayload = {
  developer_address: string
  model_id: string
  prompt: string
  min_tier: number
  zdr_required: boolean
  verifier_count: number
  metadata: Record<string, unknown>
}

export type CoverageQuote = {
  request_id: string
  coverage_available: boolean
  recommendation: string
}

export type DisputeRecord = {
  request_id: string
  task_id: string
  developer_address: string
  evidence_hash: string
  evidence_uri: string
  notes?: string | null
  created_at: string
}

export async function createInferenceRequest(payload: CreateInferencePayload) {
  const { data } = await apiClient.post<InferenceRequestRecord>('/v1/inference/requests', payload)
  return data
}

export async function getInferenceRequest(requestId: string) {
  const { data } = await apiClient.get<InferenceRequestRecord>(`/v1/inference/${requestId}`)
  return data
}

export async function listInferenceRequests() {
  const { data } = await apiClient.get<InferenceRequestRecord[]>('/v1/inference')
  return data
}

export async function getCoverageQuote(requestId: string) {
  const { data } = await apiClient.get<CoverageQuote>(`/v1/coverage/${requestId}`)
  return data
}

export async function submitDispute(
  requestId: string,
  payload: {
    developer_address: string
    evidence_hash: string
    evidence_uri: string
    notes?: string
  },
) {
  const { data } = await apiClient.post<DisputeRecord>(`/v1/disputes/${requestId}`, payload)
  return data
}

export async function getDispute(requestId: string) {
  const { data } = await apiClient.get<DisputeRecord>(`/v1/disputes/${requestId}`)
  return data
}
