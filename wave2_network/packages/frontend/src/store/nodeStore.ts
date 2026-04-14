import { create } from 'zustand'

type NodeState = {
  nodes: string[]
}

export const useNodeStore = create<NodeState>(() => ({
  nodes: [],
}))
