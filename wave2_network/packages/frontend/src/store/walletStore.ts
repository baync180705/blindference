import { create } from 'zustand'

type WalletState = {
  connected: boolean
}

export const useWalletStore = create<WalletState>(() => ({
  connected: false,
}))
