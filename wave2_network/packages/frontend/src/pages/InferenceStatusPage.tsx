import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import {
  getCoverageQuote,
  getDispute,
  getInferenceRequest,
  type CoverageQuote,
  type DisputeRecord,
  submitDispute,
  type InferenceRequestRecord,
} from '../api/inferenceApi'
import { DisputeForm } from '../components/DisputeForm'
import { PageSection } from '../components/PageSection'
import { QuorumVisualizer } from '../components/QuorumVisualizer'
import { ResultViewer } from '../components/ResultViewer'
import { formatTimestamp } from '../utils/formatters'

export function InferenceStatusPage() {
  const { requestId = '' } = useParams()
  const [request, setRequest] = useState<InferenceRequestRecord | null>(null)
  const [coverageQuote, setCoverageQuote] = useState<CoverageQuote | null>(null)
  const [dispute, setDispute] = useState<DisputeRecord | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!requestId) return

    let active = true
    let timer: number | undefined

    const poll = async () => {
      try {
        const [nextRequest, nextCoverage] = await Promise.all([
          getInferenceRequest(requestId),
          getCoverageQuote(requestId).catch(() => null),
        ])
        if (!active) return
        setRequest(nextRequest)
        setCoverageQuote(nextCoverage)

        if (nextRequest.status === 'disputed') {
          const nextDispute = await getDispute(requestId).catch(() => null)
          if (active) setDispute(nextDispute)
        }

        if (nextRequest.status === 'queued') {
          timer = window.setTimeout(poll, 4000)
        }
      } catch (pollError) {
        if (!active) return
        setError(pollError instanceof Error ? pollError.message : 'Failed to load request.')
      }
    }

    void poll()

    return () => {
      active = false
      if (timer) window.clearTimeout(timer)
    }
  }, [requestId])

  if (error) {
    return (
      <PageSection title="Signal Status" description="Unable to load the Blindference request.">
        <p className="text-sm text-rose-300">{error}</p>
      </PageSection>
    )
  }

  if (!request) {
    return (
      <PageSection title="Signal Status" description="Loading the current quorum state from ICL.">
        <p className="text-sm text-slate-300">Polling the local Blindference stack…</p>
      </PageSection>
    )
  }

  const coverageRequested = Boolean(request.metadata.coverage_requested)
  const disputeDisabled = request.status !== 'accepted' && request.status !== 'disputed'

  return (
    <div className="grid gap-6">
      <PageSection
        title="Signal Status"
        description={`Request ${request.request_id} · updated ${formatTimestamp(request.updated_at)}`}
      >
        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Asset</p>
            <p className="mt-2 text-2xl font-semibold text-white">{String(request.metadata.asset ?? 'ETH')}</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Provider</p>
            <p className="mt-2 text-2xl font-semibold text-white">{String(request.metadata.provider ?? 'groq')}</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Coverage</p>
            <p className="mt-2 text-2xl font-semibold text-white">{coverageRequested ? 'On' : 'Off'}</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Confidence</p>
            <p className="mt-2 text-2xl font-semibold text-white">{request.aggregated_confidence ?? 0}%</p>
          </div>
        </div>
      </PageSection>

      <QuorumVisualizer request={request} />
      <ResultViewer request={request} />

      <div className="grid gap-6 lg:grid-cols-[1fr,1fr]">
        <section className="rounded-[28px] border border-slate-800 bg-slate-950/60 p-5">
          <p className="text-xs uppercase tracking-[0.25em] text-emerald-300">Coverage</p>
          <h3 className="mt-1 text-xl font-semibold text-white">Protection status</h3>
          <p className="mt-4 text-sm leading-7 text-slate-200">
            {coverageRequested
              ? coverageQuote?.recommendation ?? 'Coverage requested. Waiting for the quote surface.'
              : 'Coverage was not selected for this request.'}
          </p>
        </section>

        <DisputeForm
          developerAddress={request.developer_address}
          disabled={disputeDisabled}
          onSubmit={async ({ developerAddress, evidenceUri, notes }) => {
            const evidenceHash = `demo:${request.task_id}:${Date.now()}`
            const nextDispute = await submitDispute(request.request_id, {
              developer_address: developerAddress,
              evidence_hash: evidenceHash,
              evidence_uri: evidenceUri,
              notes,
            })
            setDispute(nextDispute)
            const refreshed = await getInferenceRequest(request.request_id)
            setRequest(refreshed)
          }}
        />
      </div>

      {dispute ? (
        <section className="rounded-[28px] border border-amber-500/30 bg-amber-500/10 p-5">
          <p className="text-xs uppercase tracking-[0.25em] text-amber-200">Dispute Submitted</p>
          <p className="mt-3 text-sm leading-7 text-amber-50">
            Evidence URI: {dispute.evidence_uri}
            <br />
            Filed at: {formatTimestamp(dispute.created_at)}
          </p>
        </section>
      ) : null}
    </div>
  )
}
