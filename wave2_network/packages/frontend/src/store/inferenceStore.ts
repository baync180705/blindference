import { create } from 'zustand'

type InferenceState = {
  status: string
}

export const useInferenceStore = create<InferenceState>(() => ({
  status: 'idle',
}))
