import { useState } from 'react'
import { Dialog } from '@headlessui/react'
import { AlertCircle, X } from 'lucide-react'

import { coverageApi } from '../api/coverageApi'

interface DisputeFormProps {
  requestId: string
  coverageId: string
  taskId: string
  developerAddress: string
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function DisputeForm({
  requestId,
  coverageId,
  taskId,
  developerAddress,
  isOpen,
  onClose,
  onSuccess,
}: DisputeFormProps) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setError('')
    try {
      await coverageApi.fileDispute(requestId, {
        developer_address: developerAddress,
        evidence_hash: `demo:${taskId}:${Date.now()}`,
        evidence_uri: `inline://${taskId}`,
        notes: reason,
      })
      onSuccess()
      onClose()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to submit dispute. Try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog className="relative z-50" onClose={onClose} open={isOpen}>
      <div aria-hidden="true" className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="relative w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-[#0a0a0b] p-6 shadow-2xl">
          <button
            className="absolute right-4 top-4 text-gray-500 transition-colors hover:text-white"
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="mb-1 flex items-center gap-3">
            <div className="rounded-full border border-red-500/20 bg-red-500/10 p-2 text-red-500">
              <AlertCircle className="h-5 w-5" />
            </div>
            <Dialog.Title className="text-xl font-bold text-white">File Dispute</Dialog.Title>
          </div>
          <Dialog.Description className="mb-6 pl-12 text-sm text-gray-500">
            Explain why you believe this prediction was incorrect. Please provide relevant context.
          </Dialog.Description>

          {error ? (
            <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>
          ) : null}

          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-[11px] font-bold uppercase tracking-widest text-gray-500">
                Reason for Dispute
              </label>
              <textarea
                className="w-full resize-none rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm text-white shadow-sm outline-none transition-all focus:border-red-500/50 focus:ring-2 focus:ring-red-500/50"
                onChange={(event) => setReason(event.target.value)}
                placeholder="e.g., The model predicted high risk but the loan performed normally..."
                rows={4}
                value={reason}
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-3 border-t border-white/5 pt-4">
            <button
              className="rounded border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-bold uppercase tracking-widest text-gray-400 transition-colors hover:bg-white/[0.05]"
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>
            <button
              className="flex min-w-[140px] items-center justify-center rounded bg-emerald-500 px-6 py-2 text-sm font-bold uppercase tracking-widest text-black shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all hover:bg-emerald-400 disabled:opacity-50"
              disabled={isSubmitting || !reason.trim()}
              onClick={handleSubmit}
              type="button"
            >
              {isSubmitting ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-900/40 border-t-black" />
              ) : (
                'Submit'
              )}
            </button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
