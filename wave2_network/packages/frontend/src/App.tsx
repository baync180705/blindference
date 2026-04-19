import { Link, Route, Routes } from 'react-router-dom'

import { CoveragePage } from './pages/CoveragePage'
import { DashboardPage } from './pages/DashboardPage'
import { HomePage } from './pages/HomePage'
import { InferenceNewPage } from './pages/InferenceNewPage'
import { InferenceStatusPage } from './pages/InferenceStatusPage'
import { ModelDetailPage } from './pages/ModelDetailPage'
import { ModelMarketplacePage } from './pages/ModelMarketplacePage'
import { NodeDetailPage } from './pages/NodeDetailPage'
import { NodeExplorerPage } from './pages/NodeExplorerPage'
import { NodeJoinPage } from './pages/NodeJoinPage'

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/models', label: 'Models' },
  { to: '/nodes', label: 'Nodes' },
  { to: '/inference/new', label: 'Request Signal' },
  { to: '/coverage', label: 'Coverage' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/node/join', label: 'Join Node' },
]

export default function App() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.22),_transparent_38%),linear-gradient(180deg,_#07111f,_#020617_58%,_#041521)] text-slate-100">
      <header className="border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-xl">
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-4">
          <span className="text-lg font-semibold tracking-wide">Blindference Wave 2</span>
          {navLinks.map((link) => (
            <Link key={link.to} className="text-sm text-slate-300 hover:text-white" to={link.to}>
              {link.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/models" element={<ModelMarketplacePage />} />
          <Route path="/models/:id" element={<ModelDetailPage />} />
          <Route path="/nodes" element={<NodeExplorerPage />} />
          <Route path="/nodes/:address" element={<NodeDetailPage />} />
          <Route path="/inference/new" element={<InferenceNewPage />} />
          <Route path="/inference/:requestId" element={<InferenceStatusPage />} />
          <Route path="/coverage" element={<CoveragePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/node/join" element={<NodeJoinPage />} />
        </Routes>
      </main>
    </div>
  )
}
