import { BrowserRouter, Link, Outlet, Route, Routes } from 'react-router-dom'
import { useAccount, useConnect, useDisconnect } from 'wagmi'

import { HomePage } from './pages/HomePage'
import { InferenceNewPage } from './pages/InferenceNewPage'
import { InferenceStatusPage } from './pages/InferenceStatusPage'
import { truncateAddress } from './utils/helpers'

function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <h1 className="mb-3 text-2xl font-bold text-white">{title}</h1>
      <p className="text-sm text-gray-500">This module is under development for the Wave 2 demo.</p>
    </div>
  )
}

function WalletBadge() {
  const { address, isConnected } = useAccount()
  const { connectors, connect, isPending } = useConnect()
  const { disconnect } = useDisconnect()

  const injectedConnector = connectors[0]

  if (isConnected && address) {
    return (
      <button
        className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-right transition-colors hover:border-emerald-500/40"
        onClick={() => disconnect()}
        type="button"
      >
        <span className="block text-[10px] font-bold uppercase tracking-widest text-gray-500">Arbitrum Sepolia</span>
        <span className="font-mono text-sm text-emerald-400">{truncateAddress(address)}</span>
      </button>
    )
  }

  return (
    <button
      className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-right transition-colors hover:border-emerald-500/30 hover:text-white disabled:opacity-50"
      disabled={!injectedConnector || isPending}
      onClick={() => {
        if (injectedConnector) {
          connect({ connector: injectedConnector })
        }
      }}
      type="button"
    >
      <span className="block text-[10px] font-bold uppercase tracking-widest text-gray-500">Wallet</span>
      <span className="font-mono text-sm text-emerald-400">{isPending ? 'Connecting...' : 'Connect'}</span>
    </button>
  )
}

function Layout() {
  return (
    <div className="flex min-h-screen flex-col items-center bg-[#0a0a0b] font-sans text-[#e2e2e4] selection:bg-emerald-500/30">
      <header className="sticky top-0 z-30 w-full border-b border-white/5 bg-[#0a0a0b]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-8">
            <Link className="flex items-center group" to="/">
              <span className="text-lg font-bold tracking-tight text-white">
                Blindference Wave <span className="font-medium text-gray-300">2</span>
              </span>
            </Link>
            <nav className="hidden gap-5 text-[13px] font-medium text-gray-400 md:flex lg:gap-7">
              <Link className="transition-colors hover:text-white" to="/">
                Home
              </Link>
              <Link className="transition-colors hover:text-white" to="/models">
                Models
              </Link>
              <Link className="transition-colors hover:text-white" to="/nodes">
                Nodes
              </Link>
              <Link className="transition-colors hover:text-white" to="/inference/new">
                Request Signal
              </Link>
              <Link className="transition-colors hover:text-white" to="/coverage">
                Coverage
              </Link>
              <Link className="transition-colors hover:text-white" to="/dashboard">
                Dashboard
              </Link>
              <Link className="transition-colors hover:text-white" to="/join-node">
                Join Node
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <WalletBadge />
            <div className="h-8 w-8 rounded-full border border-white/10 bg-gradient-to-tr from-emerald-500 to-blue-500" />
          </div>
        </div>
      </header>
      <main className="mx-auto flex-1 w-full max-w-6xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="mt-auto flex h-10 w-full items-center border-t border-white/5 bg-black px-4 py-3">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                ICL Gateway: Online
              </span>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                Quorum: 1 leader + 2 verifiers
              </span>
            </div>
          </div>
          <div className="font-mono text-[10px] text-gray-600">v2.4.0-stable | cofhe-sdk live</div>
        </div>
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />} path="/">
          <Route element={<HomePage />} index />
          <Route element={<Placeholder title="Model Marketplace" />} path="models" />
          <Route element={<Placeholder title="Network Nodes" />} path="nodes" />
          <Route element={<InferenceNewPage />} path="inference/new" />
          <Route element={<InferenceStatusPage />} path="inference/:requestId" />
          <Route element={<Placeholder title="Inference Coverage" />} path="coverage" />
          <Route element={<Placeholder title="User Dashboard" />} path="dashboard" />
          <Route element={<Placeholder title="Join the Network" />} path="join-node" />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
