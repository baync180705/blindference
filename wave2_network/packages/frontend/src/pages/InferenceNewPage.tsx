import { useNavigate } from 'react-router-dom'
import { useAccount, usePublicClient, useWalletClient } from 'wagmi'
import { Lock, ShieldAlert } from 'lucide-react'
import { PermitUtils } from '@cofhe/sdk/permits'
import type { Hex } from 'viem'
import axios from 'axios'

import { inferenceApi } from '../api/inferenceApi'
import { useCofheClient } from '../hooks/useCofheClient'
import { readStoredRiskInputHandles, storeEncryptedRiskInputsInVault } from '../lib/inputVault'
import { useInferenceStore } from '../stores/inferenceStore'
import { encryptRiskFeatures } from '../utils/encryption'
import { cn } from '../utils/helpers'

const MODEL_BINDINGS = {
  'llama3-70b': {
    modelId: 'groq:llama-3.3-70b-versatile',
    provider: 'groq',
    model: 'llama-3.3-70b-versatile',
    baseFee: 10,
    telemetry: {
      accuracy: '94.2%',
      falsePositives: '1.2%',
      hallucinations: '< 0.5%',
      benchmark: '82.0 MMLU',
    },
  },
  'gemini-pro': {
    modelId: 'gemini:gemini-2.5-flash',
    provider: 'gemini',
    model: 'gemini-2.5-flash',
    baseFee: 8,
    telemetry: {
      accuracy: '96.8%',
      falsePositives: '0.8%',
      hallucinations: '< 0.2%',
      benchmark: '86.2 MMLU',
    },
  },
} as const

export function InferenceNewPage() {
  const navigate = useNavigate()
  const { address } = useAccount()
  const publicClient = usePublicClient()
  const { data: walletClient } = useWalletClient()
  const { client, isReady } = useCofheClient()
  const store = useInferenceStore()

  const currentModel = MODEL_BINDINGS[store.modelId]
  const basePrice = currentModel.baseFee
  const coveragePremium = store.coverageEnabled ? 2 : 0
  const totalDisplay = basePrice + coveragePremium

  const handleSubmit = async () => {
    if (store.creditScore < 300 || store.creditScore > 850) {
      store.setError('Invalid credit score. Must be between 300 and 850.')
      return
    }

    if (!client || !isReady || !address) {
      store.setError('Connect your wallet and wait for CoFHE to initialize.')
      return
    }
    if (!walletClient || !publicClient) {
      store.setError('Wallet client is not available yet.')
      return
    }

    const inputVaultAddress = import.meta.env.VITE_BLINDFERENCE_INPUT_VAULT_ADDRESS as Hex | undefined
    if (!inputVaultAddress) {
      store.setError('VITE_BLINDFERENCE_INPUT_VAULT_ADDRESS is not configured.')
      return
    }

    try {
      store.setError(null)
      store.setIsEncrypting(true)
      const loanId = `loan_${Date.now()}`

      const encrypted = await encryptRiskFeatures(client, {
        creditScore: store.creditScore,
        loanAmount: store.loanAmount,
        accountAge: store.accountAge,
        prevDefaults: store.prevDefaults,
      })

      const inputVaultTx = await storeEncryptedRiskInputsInVault({
        encryptedInputs: encrypted,
        loanId,
        publicClient,
        vaultAddress: inputVaultAddress,
        walletClient,
      })

      const storedVaultInputs = await readStoredRiskInputHandles({
        loanId,
        publicClient,
        vaultAddress: inputVaultAddress,
      })
      if (storedVaultInputs.owner.toLowerCase() !== address.toLowerCase()) {
        throw new Error('BlindferenceInputVault stored handles for a different owner than the connected wallet.')
      }

      const vaultBackedEncryptedInput = encrypted.map((item, index) => ({
        ctHash: storedVaultInputs.handles[index].toString(),
        utype: item.utype,
        signature: item.signature,
      }))

      const quorumPreview = await inferenceApi.getQuorumPreview({
        model_id: currentModel.modelId,
        min_tier: 1,
        verifier_count: 2,
        zdr_required: false,
      })
      const quorumNodes = [quorumPreview.data.leader, ...quorumPreview.data.verifiers]

      const permits = await Promise.all(
        quorumNodes.map(async (nodeAddress) => {
          const sharingPermit = await client.permits.createSharing({
            issuer: address,
            recipient: nodeAddress,
            name: `Blindference ${currentModel.modelId} ${Date.now()} -> ${nodeAddress}`,
          })
          return {
            node: nodeAddress,
            permit: PermitUtils.export(sharingPermit),
          }
        }),
      )

      store.setIsEncrypting(false)
      store.setIsSubmitting(true)

      const response = await inferenceApi.submit({
        model_id: currentModel.modelId,
        encrypted_input: vaultBackedEncryptedInput,
        permits,
        leader_address: quorumPreview.data.leader,
        verifier_addresses: quorumPreview.data.verifiers,
        feature_types: ['uint32', 'uint64', 'uint32', 'uint8'],
        loan_id: loanId,
        coverage_type: store.coverageEnabled ? 'HALLUCINATION' : null,
        max_fee_gnk: totalDisplay,
        developer_address: address,
        min_tier: 1,
        zdr_required: false,
        verifier_count: 2,
        metadata: {
          coverage_requested: store.coverageEnabled,
          encryption_mode: 'cofhe',
          input_vault_address: inputVaultAddress,
          input_vault_tx: inputVaultTx,
          input_vault_owner: storedVaultInputs.owner,
          input_vault_stored_at: storedVaultInputs.storedAt.toString(),
          vertical: 'blindference-risk-demo',
          provider: currentModel.provider,
          model: currentModel.model,
        },
      })

      store.setRequestId(response.data.request_id)
      navigate(`/inference/${response.data.request_id}`)
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail
        if (typeof detail === 'string' && detail.trim()) {
          store.setError(detail)
          return
        }
      }
      store.setError(error instanceof Error ? error.message : 'Failed to submit request.')
    } finally {
      store.setIsSubmitting(false)
      store.setIsEncrypting(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl pb-20 pt-6">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="mb-1 text-2xl font-semibold text-white">New Risk Assessment</h1>
          <p className="text-sm text-gray-500">Secure, end-to-end encrypted inference via FHE.</p>
        </div>
        <span className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-emerald-500">
          FHE Active
        </span>
      </div>

      {store.error ? (
        <div className="mb-6 flex items-center gap-3 rounded border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-500">
          <ShieldAlert className="h-5 w-5" />
          {store.error}
        </div>
      ) : null}

      <div className="space-y-6">
        <div className="space-y-3">
          <label className="text-[11px] font-bold uppercase tracking-widest text-gray-500">Model Selection</label>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {(['llama3-70b', 'gemini-pro'] as const).map((id) => {
              const isSelected = store.modelId === id
              return (
                <button
                  className={cn(
                    'cursor-pointer rounded-lg p-3 text-left outline-none transition-colors flex flex-col gap-1',
                    isSelected
                      ? 'border-2 border-emerald-500 bg-emerald-500/5 opacity-100'
                      : 'border border-white/5 bg-white/[0.02] opacity-60 hover:border-white/20',
                  )}
                  key={id}
                  onClick={() => store.setModelId(id)}
                  type="button"
                >
                  <span className="text-sm font-semibold capitalize text-white">{id.replace('-', ' ')}</span>
                  <span className="text-[10px] text-gray-400">{id === 'gemini-pro' ? 'Google API' : 'DePIN execution'}</span>
                </button>
              )
            })}
          </div>

          <div className="mt-3 w-full space-y-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-emerald-400">
            <div className="border-b border-emerald-500/10 pb-2 text-[10px] font-bold uppercase tracking-widest text-emerald-500/70">
              Model Telemetry
            </div>
            <div className="mt-2 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
              <div>
                <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">Accuracy</span>
                <span className="font-mono">{currentModel.telemetry.accuracy}</span>
              </div>
              <div>
                <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">False Positives</span>
                <span className="font-mono">{currentModel.telemetry.falsePositives}</span>
              </div>
              <div>
                <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">Hallucinations</span>
                <span className="font-mono">{currentModel.telemetry.hallucinations}</span>
              </div>
              <div>
                <span className="mb-1 block text-[10px] uppercase text-emerald-500/50">Benchmark</span>
                <span className="font-mono">{currentModel.telemetry.benchmark}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <label className="text-[11px] font-bold uppercase tracking-widest text-gray-500">
            Applicant Data (Encrypted)
          </label>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs text-gray-400">Credit Score</span>
              <input
                className="w-full rounded border border-white/10 bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:border-emerald-500/50 focus:outline-none"
                max={850}
                min={300}
                onChange={(event) => store.setCreditScore(Number(event.target.value))}
                type="number"
                value={store.creditScore}
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs text-gray-400">Loan Amount ($)</span>
              <input
                className="w-full rounded border border-white/10 bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:border-emerald-500/50 focus:outline-none"
                min={0}
                onChange={(event) => store.setLoanAmount(Number(event.target.value))}
                type="number"
                value={store.loanAmount}
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs text-gray-400">Account Age (days)</span>
              <input
                className="w-full rounded border border-white/10 bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:border-emerald-500/50 focus:outline-none"
                min={0}
                onChange={(event) => store.setAccountAge(Number(event.target.value))}
                type="number"
                value={store.accountAge}
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs text-gray-400">Previous Defaults</span>
              <input
                className="w-full rounded border border-white/10 bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:border-emerald-500/50 focus:outline-none"
                max={10}
                min={0}
                onChange={(event) => store.setPrevDefaults(Number(event.target.value))}
                type="number"
                value={store.prevDefaults}
              />
            </div>
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-lg border border-emerald-500/20 bg-emerald-950/20 p-4">
          <input
            checked={store.coverageEnabled}
            className="mt-1 cursor-pointer rounded border-white/10 bg-black text-emerald-500 accent-emerald-500"
            onChange={(event) => store.setCoverageEnabled(event.target.checked)}
            type="checkbox"
          />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-emerald-400">Hallucination Coverage</h4>
            <p className="text-xs leading-relaxed text-gray-400">
              Receive up to 500 USDC payout if the prediction is disputed and settled in your favor. Premium is
              automatically calculated.
            </p>
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between border-t border-white/5 pt-4">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-tighter text-gray-500">Estimated Fee</span>
            <div className="text-xl font-mono text-white">
              {totalDisplay}.00 <span className="text-gray-500">GNK</span>
            </div>
          </div>

          <button
            className="flex min-w-[200px] items-center justify-center rounded bg-emerald-500 px-8 py-3 text-sm font-bold uppercase text-black shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all hover:bg-emerald-400 disabled:opacity-50 disabled:shadow-none"
            disabled={store.isEncrypting || store.isSubmitting || !isReady || !address}
            onClick={handleSubmit}
            type="button"
          >
            {store.isEncrypting ? (
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 animate-pulse text-emerald-900" />
                Encrypting...
              </div>
            ) : store.isSubmitting ? (
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-900/30 border-t-black" />
                Submitting
              </div>
            ) : (
              'Run Encrypted Inference'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
