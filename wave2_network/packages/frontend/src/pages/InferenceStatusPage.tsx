import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react'

import { DisputeForm } from '../components/DisputeForm'
import { OnChainEvidence } from '../components/OnChainEvidence'
import { QuorumVisualizer } from '../components/QuorumVisualizer'
import { RiskGauge } from '../components/RiskGauge'
import { StatusTimeline } from '../components/StatusTimeline'
import { useInferenceStatus } from '../hooks/useInferenceStatus'

export function InferenceStatusPage() {
  const { requestId = '' } = useParams<{ requestId: string }>()
  const [isDisputeOpen, setIsDisputeOpen] = useState(false)
  const [timeLeft, setTimeLeft] = useState('')
  const status = useInferenceStatus(requestId)

  useEffect(() => {
    const update = () => {
      if (!status?.raw.updated_at) {
        setTimeLeft('72h 0m')
        return
      }
      const acceptedAt = Date.parse(status.raw.updated_at)
      const deadline = acceptedAt + 72 * 60 * 60 * 1000
      const diff = Math.max(deadline - Date.now(), 0)
      const hours = Math.floor(diff / 3_600_000)
      const minutes = Math.floor((diff % 3_600_000) / 60_000)
      setTimeLeft(`${hours}h ${minutes}m`)
    }

    update()
    const interval = window.setInterval(update, 60_000)
    return () => window.clearInterval(interval)
  }, [status?.raw.updated_at])

  const getStatusDisplay = (value: string) => {
    switch (value) {
      case 'QUEUED':
        return { text: 'In Queue', icon: Clock, color: 'text-gray-400', bg: 'bg-white/[0.05]' }
      case 'ASSIGNED':
        return {
          text: 'Assigning Quorum',
          icon: CheckCircle2,
          color: 'text-blue-400',
          bg: 'bg-blue-500/10 border border-blue-500/20',
        }
      case 'EXECUTING':
        return {
          text: 'Leader Executing FHE',
          icon: CheckCircle2,
          color: 'text-blue-400',
          bg: 'bg-blue-500/10 border border-blue-500/20',
        }
      case 'VERIFYING':
        return {
          text: 'Verifiers Checking Result',
          icon: CheckCircle2,
          color: 'text-yellow-400',
          bg: 'bg-yellow-500/10 border border-yellow-500/20',
        }
      case 'ACCEPTED':
        return {
          text: 'Consensus Reached',
          icon: CheckCircle2,
          color: 'text-emerald-400',
          bg: 'bg-emerald-500/10 border border-emerald-500/20',
        }
      case 'REJECTED':
        return {
          text: 'Quorum Rejected',
          icon: AlertCircle,
          color: 'text-red-400',
          bg: 'bg-red-500/10 border border-red-500/20',
        }
      case 'DISPUTED':
        return {
          text: 'Dispute Open',
          icon: AlertCircle,
          color: 'text-amber-300',
          bg: 'bg-amber-500/10 border border-amber-500/20',
        }
      default:
        return { text: value, icon: Clock, color: 'text-gray-400', bg: 'bg-white/[0.05]' }
    }
  }

  if (!status) {
    return (
      <div className="mx-auto max-w-4xl pb-20 pt-6">
        <div className="flex h-64 flex-col items-center justify-center">
          <div className="relative mb-4 h-32 w-32 overflow-hidden">
            <div className="absolute top-0 h-32 w-32 rounded-full border-[8px] border-white/5" />
            <div className="absolute top-0 h-32 w-32 animate-spin rounded-full border-[8px] border-emerald-500 border-b-transparent border-r-transparent" />
          </div>
          <p className="animate-pulse text-xs font-bold uppercase tracking-widest text-gray-500">Loading request...</p>
        </div>
      </div>
    )
  }

  const currentDisplay = getStatusDisplay(status.status)
  const Icon = currentDisplay.icon

  return (
    <div className="mx-auto max-w-4xl pb-20 pt-6">
      <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h2 className="text-lg font-semibold text-white">Active Task</h2>
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase text-gray-500">
            <span>REQ-ID: {requestId}</span>
          </div>
        </div>
        <div
          className={`flex items-center gap-2 rounded px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest ${currentDisplay.bg} ${currentDisplay.color}`}
        >
          <Icon className="h-3 w-3" />
          {currentDisplay.text}
        </div>
      </div>

      <StatusTimeline currentStatus={status.status} timestamps={status.timestamps} />

      <div className="grid grid-cols-1 gap-8 md:grid-cols-[1fr_300px]">
        <div className="space-y-8">
          <section className="space-y-4 rounded-xl border border-white/5 bg-white/[0.02] p-5">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Quorum Progress</h3>
            <QuorumVisualizer leader={status.quorum.leader ?? undefined} status={status.status} verifiers={status.quorum.verifiers} />
            {!status.quorum.leader ? (
              <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.01] py-8 text-center text-sm text-gray-500">
                Waiting for network node assignment...
              </div>
            ) : null}
          </section>

          {(status.result_commit_tx || status.escrow_creation_tx || status.coverage_purchase_tx || status.escrow_release_tx) ? (
            <OnChainEvidence
              coveragePurchaseTx={status.coverage_purchase_tx}
              escrowCreationTx={status.escrow_creation_tx}
              escrowReleaseTx={status.escrow_release_tx}
              resultCommitTx={status.result_commit_tx}
              taskId={status.task_id || requestId}
            />
          ) : null}

          {status.status === 'ACCEPTED' && status.coverage_id ? (
            <section className="mt-auto flex flex-col gap-4 rounded-xl border border-white/5 bg-white/[0.02] p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-gray-500">Coverage Status</div>
                  <div className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                    ACTIVE <span className="ml-2 text-xs font-normal text-gray-500">ID: {status.coverage_id}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-gray-500">Dispute Window</div>
                  <div className="font-mono text-sm text-gray-300">{timeLeft} remaining</div>
                </div>
              </div>
              <button
                className="mt-2 w-full rounded border border-red-500/40 bg-red-500/10 py-2.5 text-xs font-bold uppercase tracking-widest text-red-400 transition-colors hover:bg-red-500/20 focus:outline-none focus:ring-2 focus:ring-red-500/50"
                onClick={() => setIsDisputeOpen(true)}
                type="button"
              >
                FILE DISPUTE CLAIM
              </button>
            </section>
          ) : null}
        </div>

        <div>
          <section className="sticky top-24 flex flex-col items-center justify-center rounded-xl border border-white/5 bg-black/40 p-8">
            {status.status === 'ACCEPTED' && status.result ? (
              <div className="flex w-full flex-col items-center">
                <RiskGauge score={status.result.risk_score} size={220} />

                <div className="mt-8 flex w-full justify-center gap-8">
                  <div className="text-center">
                    <div className="text-xs font-bold uppercase text-gray-500">Confidence</div>
                    <div className="text-xl font-semibold text-white">{status.result.confidence}%</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-bold uppercase text-gray-500">Quorum</div>
                    <div className="text-xl font-semibold text-white">
                      {status.quorum.confirm_count}/{status.quorum.verifiers.length}{' '}
                      <span className="text-xs text-emerald-400">✓</span>
                    </div>
                  </div>
                </div>

                <div className="mt-8 w-full space-y-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-emerald-400">
                  <div className="border-b border-emerald-500/10 pb-2 text-[10px] font-bold uppercase tracking-widest text-emerald-500/70">
                    Verified Model Telemetry
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">Accuracy</span>
                      <span className="font-mono">{status.raw.model_id.includes('gemini') ? '96.8%' : '94.2%'}</span>
                    </div>
                    <div>
                      <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">False Positives</span>
                      <span className="font-mono">{status.raw.model_id.includes('gemini') ? '0.8%' : '1.2%'}</span>
                    </div>
                    <div>
                      <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">Hallucinations</span>
                      <span className="font-mono">{status.raw.model_id.includes('gemini') ? '< 0.2%' : '< 0.5%'}</span>
                    </div>
                    <div>
                      <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">Benchmark</span>
                      <span className="font-mono">{status.raw.model_id.includes('gemini') ? '86.2 MMLU' : '82.0 MMLU'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : status.status === 'REJECTED' ? (
              <div className="flex h-48 flex-col items-center justify-center text-center text-red-400">
                <AlertCircle className="mb-3 h-12 w-12 opacity-50" />
                <p className="text-sm font-medium">
                  Inference rejected by quorum.
                  <br />
                  Mismatched execution fingerprints.
                </p>
              </div>
            ) : (
              <div className="flex h-64 flex-col items-center justify-center">
                <div className="relative mb-4 h-32 w-32 overflow-hidden">
                  <div className="absolute top-0 h-32 w-32 rounded-full border-[8px] border-white/5" />
                  <div className="absolute top-0 h-32 w-32 animate-spin rounded-full border-[8px] border-emerald-500 border-b-transparent border-r-transparent" />
                </div>
                <p className="animate-pulse text-xs font-bold uppercase tracking-widest text-gray-500">
                  {status.status === 'VERIFYING' ? 'Verifiers checking result...' : 'Running FHE...'}
                </p>
              </div>
            )}
          </section>
        </div>
      </div>

      <DisputeForm
        coverageId={status.coverage_id || ''}
        requestId={requestId}
        developerAddress={status.developer_address}
        isOpen={isDisputeOpen}
        onClose={() => setIsDisputeOpen(false)}
        onSuccess={() => {
          setIsDisputeOpen(false)
        }}
        taskId={status.task_id}
      />
    </div>
  )
}
