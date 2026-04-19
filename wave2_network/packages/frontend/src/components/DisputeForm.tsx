import { useState } from 'react'

type DisputeFormProps = {
  developerAddress: string
  disabled?: boolean
  onSubmit: (payload: { developerAddress: string; evidenceUri: string; notes: string }) => Promise<void>
}

export function DisputeForm({ developerAddress, disabled = false, onSubmit }: DisputeFormProps) {
  const [evidenceUri, setEvidenceUri] = useState('ipfs://demo-evidence')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  return (
    <form
      className="grid gap-4 rounded-[28px] border border-amber-500/30 bg-amber-500/10 p-5"
      onSubmit={async (event) => {
        event.preventDefault()
        setSubmitting(true)
        try {
          await onSubmit({ developerAddress, evidenceUri, notes })
        } finally {
          setSubmitting(false)
        }
      }}
    >
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-amber-200">Dispute Window</p>
        <h3 className="mt-1 text-xl font-semibold text-white">File an insured-output dispute</h3>
      </div>

      <label className="grid gap-2 text-sm text-slate-100">
        Evidence URI
        <input
          className="rounded-2xl border border-amber-400/20 bg-slate-950/70 px-4 py-3 outline-none transition focus:border-amber-300"
          value={evidenceUri}
          onChange={(event) => setEvidenceUri(event.target.value)}
        />
      </label>

      <label className="grid gap-2 text-sm text-slate-100">
        Notes
        <textarea
          className="min-h-32 rounded-2xl border border-amber-400/20 bg-slate-950/70 px-4 py-3 outline-none transition focus:border-amber-300"
          placeholder="Explain why the signal looks incorrect or hallucinated."
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </label>

      <button
        className="inline-flex items-center justify-center rounded-full bg-amber-300 px-5 py-3 font-semibold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
        disabled={disabled || submitting}
        type="submit"
      >
        {submitting ? 'Submitting…' : 'File Dispute'}
      </button>
    </form>
  )
}
