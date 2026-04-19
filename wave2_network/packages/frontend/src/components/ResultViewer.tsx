import type { InferenceRequestRecord } from '../api/inferenceApi'
import { formatTxUrl } from '../utils/formatters'

type ResultViewerProps = {
  request: InferenceRequestRecord
}

function parseResultPreview(resultPreview: string | null) {
  if (!resultPreview) return null
  try {
    return JSON.parse(resultPreview) as {
      asset?: string
      signal?: string
      confidence?: number
      provider?: string
      model?: string
      response_text?: string
      response_hash?: string
    }
  } catch {
    return null
  }
}

export function ResultViewer({ request }: ResultViewerProps) {
  const parsed = parseResultPreview(request.result_preview)
  const txUrl = formatTxUrl(request.chain_tx_hash)

  return (
    <div className="rounded-[28px] border border-slate-800 bg-slate-950/60 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-emerald-300">Result</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Blindference insured AI output</h2>
        </div>
        <div className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
          Status: {request.status.toUpperCase()}
        </div>
      </div>

      {parsed ? (
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Signal</p>
            <p className="mt-3 text-3xl font-semibold text-white">{parsed.signal ?? 'Pending'}</p>
            <p className="mt-1 text-sm text-slate-300">{parsed.asset ?? 'Unknown asset'}</p>
          </div>

          <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Confidence</p>
            <p className="mt-3 text-3xl font-semibold text-white">
              {parsed.confidence ?? request.aggregated_confidence ?? 0}%
            </p>
            <p className="mt-1 text-sm text-slate-300">{parsed.provider ?? 'provider'} · {parsed.model ?? 'model'}</p>
          </div>

          <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Commitment</p>
            <p className="mt-3 break-all font-mono text-xs text-slate-200">
              {parsed.response_hash ?? request.result_hash ?? 'Pending'}
            </p>
          </div>
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-300">
          The node runtime has not committed a structured result yet. Once a quorum accepts the response, the AI
          output will appear here automatically.
        </div>
      )}

      <div className="mt-5 rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Model reasoning</p>
        <p className="mt-3 text-sm leading-7 text-slate-200">
          {parsed?.response_text ?? request.result_preview ?? 'Waiting for the leader node to submit a result.'}
        </p>
      </div>

      {txUrl ? (
        <a
          className="mt-5 inline-flex items-center rounded-full border border-cyan-400/40 px-4 py-2 text-sm text-cyan-200 transition hover:border-cyan-300 hover:text-cyan-100"
          href={txUrl}
          rel="noreferrer"
          target="_blank"
        >
          View transaction on Arbiscan
        </a>
      ) : null}
    </div>
  )
}
