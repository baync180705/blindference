import { createConfig, http } from 'wagmi'
import { arbitrumSepolia, hardhat } from 'wagmi/chains'
import { injected, walletConnect } from 'wagmi/connectors'

const walletConnectProjectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID

export const wagmiConfig = createConfig({
  chains: [arbitrumSepolia, hardhat],
  connectors: [
    injected(),
    ...(walletConnectProjectId
      ? [
          walletConnect({
            projectId: walletConnectProjectId,
            showQrModal: true,
          }),
        ]
      : []),
  ],
  transports: {
    [arbitrumSepolia.id]: http(),
    [hardhat.id]: http('http://127.0.0.1:8545'),
  },
})
