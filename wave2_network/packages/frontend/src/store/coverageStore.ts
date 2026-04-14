import { create } from 'zustand'

type CoverageState = {
  coverageIds: string[]
}

export const useCoverageStore = create<CoverageState>(() => ({
  coverageIds: [],
}))
