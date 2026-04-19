import type { InferenceRequestRecord } from '../api/inferenceApi'
import { formatAddress } from '../utils/formatters'

type QuorumVisualizerProps = {
  request: InferenceRequestRecord
}

export function QuorumVisualizer({ request }: QuorumVisualizerProps) {
  const totalVotes = request.confirm_count + request.reject_count
  const plannedVotes = request.quorum.verifier_addresses.length

  return (
    <div className="rounded-[28px] border border-slate-800 bg-slate-950/60 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Quorum</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Leader + verifier progress</h2>
        </div>
        <div className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
          {totalVotes}/{plannedVotes} verifier votes
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-cyan-200">Leader</p>
          <p className="mt-2 font-mono text-sm text-white">{formatAddress(request.quorum.leader_address)}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Verifiers</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {request.quorum.verifier_addresses.map((address) => (
              <span
                key={address}
                className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 font-mono text-xs text-slate-200"
              >
                {formatAddress(address)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-300 transition-all"
          style={{ width: `${plannedVotes === 0 ? 0 : (totalVotes / plannedVotes) * 100}%` }}
        />
      </div>
    </div>
  )
}
