import { create } from 'zustand';

interface InferenceState {
  // Form state
  modelId: 'llama3-70b' | 'gemini-pro';
  creditScore: number;
  loanAmount: number;
  accountAge: number;
  prevDefaults: number;
  coverageEnabled: boolean;
  
  // Submission state
  isEncrypting: boolean;
  isSubmitting: boolean;
  requestId: string | null;
  error: string | null;
  
  // Actions
  setModelId: (id: 'llama3-70b' | 'gemini-pro') => void;
  setCreditScore: (val: number) => void;
  setLoanAmount: (val: number) => void;
  setAccountAge: (val: number) => void;
  setPrevDefaults: (val: number) => void;
  setCoverageEnabled: (enabled: boolean) => void;
  setIsEncrypting: (isEncrypting: boolean) => void;
  setIsSubmitting: (isSubmitting: boolean) => void;
  setRequestId: (requestId: string | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  modelId: 'gemini-pro' as const,
  creditScore: 720,
  loanAmount: 25000,
  accountAge: 1200,
  prevDefaults: 2,
  coverageEnabled: false,
  isEncrypting: false,
  isSubmitting: false,
  requestId: null,
  error: null,
};

export const useInferenceStore = create<InferenceState>((set) => ({
  ...initialState,
  setModelId: (modelId) => set({ modelId }),
  setCreditScore: (creditScore) => set({ creditScore }),
  setLoanAmount: (loanAmount) => set({ loanAmount }),
  setAccountAge: (accountAge) => set({ accountAge }),
  setPrevDefaults: (prevDefaults) => set({ prevDefaults }),
  setCoverageEnabled: (coverageEnabled) => set({ coverageEnabled }),
  setIsEncrypting: (isEncrypting) => set({ isEncrypting }),
  setIsSubmitting: (isSubmitting) => set({ isSubmitting }),
  setRequestId: (requestId) => set({ requestId }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
