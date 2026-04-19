import { useState } from 'react'

import { MODEL_OPTIONS, SIGNAL_ASSETS } from '../utils/constants'

type InferenceFormProps = {
  onSubmit: (payload: {
    asset: string
    maxFee: string
    developerAddress: string
    providerModel: string
    coverageRequested: boolean
  }) => Promise<void>
  submitting?: boolean
}

export function InferenceForm({ onSubmit, submitting = false }: InferenceFormProps) {
  const [asset, setAsset] = useState<string>('ETH')
  const [maxFee, setMaxFee] = useState('25')
  const [developerAddress, setDeveloperAddress] = useState('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266')
  const [providerModel, setProviderModel] = useState<string>(MODEL_OPTIONS[0].value)
  const [coverageRequested, setCoverageRequested] = useState(true)

  return (
    <form
      className="grid gap-5"
      onSubmit={async (event) => {
        event.preventDefault()
        await onSubmit({ asset, maxFee, developerAddress, providerModel, coverageRequested })
      }}
    >
      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-2 text-sm text-slate-200">
          Asset
          <select
            className="rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 outline-none transition focus:border-cyan-400"
            value={asset}
            onChange={(event) => setAsset(event.target.value)}
          >
            {SIGNAL_ASSETS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-2 text-sm text-slate-200">
          Max Fee
          <input
            className="rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 outline-none transition focus:border-cyan-400"
            value={maxFee}
            onChange={(event) => setMaxFee(event.target.value)}
            placeholder="25"
          />
        </label>
      </div>

      <label className="grid gap-2 text-sm text-slate-200">
        Developer Wallet
        <input
          className="rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 outline-none transition focus:border-cyan-400"
          value={developerAddress}
          onChange={(event) => setDeveloperAddress(event.target.value)}
          placeholder="0x..."
        />
      </label>

      <label className="grid gap-2 text-sm text-slate-200">
        Cloud Model
        <select
          className="rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 outline-none transition focus:border-cyan-400"
          value={providerModel}
          onChange={(event) => setProviderModel(event.target.value)}
        >
          {MODEL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
        <input
          checked={coverageRequested}
          className="size-4 rounded border-slate-500 bg-transparent"
          type="checkbox"
          onChange={(event) => setCoverageRequested(event.target.checked)}
        />
        Purchase coverage for hallucination and false-signal protection
      </label>

      <button
        className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
        disabled={submitting}
        type="submit"
      >
        {submitting ? 'Submitting…' : 'Request Signal'}
      </button>
    </form>
  )
}
