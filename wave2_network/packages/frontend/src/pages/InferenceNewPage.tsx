import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createInferenceRequest } from '../api/inferenceApi'
import { InferenceForm } from '../components/InferenceForm'
import { PageSection } from '../components/PageSection'
import { WalletConnect } from '../components/WalletConnect'

export function InferenceNewPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr,0.9fr]">
      <PageSection
        title="Request Signal"
        description="Submit an insured inference request to the Blindference CNN. Groq or Gemini generates the signal off-chain, Reineira-backed settlement protects the outcome."
      >
        <div className="mb-6">
          <WalletConnect />
        </div>

        <InferenceForm
          submitting={submitting}
          onSubmit={async ({ asset, maxFee, developerAddress, providerModel, coverageRequested }) => {
            setSubmitting(true)
            setError(null)

            try {
              const [provider, model] = providerModel.split(':')
              const request = await createInferenceRequest({
                developer_address: developerAddress,
                model_id: providerModel,
                prompt: `Provide a short-term trading signal for ${asset} with concise rationale and explicit confidence.`,
                min_tier: 1,
                zdr_required: false,
                verifier_count: 2,
                metadata: {
                  asset,
                  max_fee: maxFee,
                  provider,
                  model,
                  coverage_requested: coverageRequested,
                  vertical: 'blindference-demo',
                },
              })
              navigate(`/inference/${request.request_id}`)
            } catch (submitError) {
              setError(submitError instanceof Error ? submitError.message : 'Failed to create request.')
            } finally {
              setSubmitting(false)
            }
          }}
        />

        {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
      </PageSection>

      <aside className="grid gap-6">
        <section className="rounded-[28px] border border-slate-800 bg-slate-950/60 p-6">
          <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Flow</p>
          <ol className="mt-4 grid gap-3 text-sm text-slate-300">
            <li>1. ICL assigns one leader and a verifier quorum.</li>
            <li>2. The node runtime calls Groq or Gemini and hashes the response.</li>
            <li>3. Result commitment lands on Arbitrum via the Reineira protocol stack.</li>
            <li>4. Coverage and dispute hooks stay open for the 72-hour window.</li>
          </ol>
        </section>

        <section className="rounded-[28px] border border-emerald-500/20 bg-emerald-500/10 p-6">
          <p className="text-xs uppercase tracking-[0.25em] text-emerald-200">Coverage</p>
          <p className="mt-3 text-sm leading-7 text-emerald-50">
            This demo treats coverage as a first-class product surface, not a side note. Users can request an AI
            output, see the quorum record, and dispute bad results under the same flow.
          </p>
        </section>
      </aside>
    </div>
  )
}
