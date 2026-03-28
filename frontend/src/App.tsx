import { useState, useEffect } from 'react';
import { useWeb3 } from './hooks/useWeb3';
import { Model } from './services/fheService';
import Marketplace from './pages/Marketplace';
import InferencePortal from './pages/InferencePortal';
import LabDashboard from './pages/LabDashboard';
import DatasetUpload from './pages/DatasetUpload';
import { Button } from './components/UI';
import { CursorEffect } from './components/CursorEffect';
import { LayeredStack } from './components/LayeredStack';
import { Shield, LayoutDashboard, ShoppingBag, Beaker, Wallet, LogOut, Github, Twitter, MessageSquare, ArrowRight, Cpu, Lock } from 'lucide-react';
import { cn } from './lib/utils';
import { motion, AnimatePresence } from 'motion/react';

type Tab = 'marketplace' | 'inference' | 'lab' | 'dataset_upload';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab | 'home'>('home');
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [selectedLabAddress, setSelectedLabAddress] = useState<string | null>(null);
  const { address, isConnecting, authError, isRegistrationNeeded, connect, disconnect, register, setIsRegistrationNeeded, role } = useWeb3();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleSelectModel = (model: Model) => {
    setSelectedModel(model);
    setActiveTab('inference');
  };

  const handleSelectLab = (address: string) => {
    setSelectedLabAddress(address);
    setActiveTab('dataset_upload');
  };

  const NavItem = ({ id, label }: { id: Tab | 'home'; label: string }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={cn(
        'px-4 py-1.5 rounded-full transition-all duration-300 text-[11px] font-bold uppercase tracking-widest',
        activeTab === id 
          ? 'bg-white text-black' 
          : 'text-white/60 hover:text-white'
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-main)] selection:bg-[var(--accent-cyan)]/30">
      <CursorEffect />

      {/* Floating Navbar */}
      <div className="fixed top-6 left-0 w-full z-[100] flex justify-center px-6">
        <motion.header 
          initial={{ y: -100 }}
          animate={{ y: 0 }}
          className={cn(
            'glass-pill rounded-full px-2 py-2 flex items-center gap-6 transition-all duration-500',
            scrolled ? 'scale-95' : 'scale-100'
          )}
        >
          <div className="flex items-center gap-3 pl-4 pr-6 border-r border-white/10">
            <Shield className="w-5 h-5 text-[var(--accent-cyan)]" />
            <span className="text-sm font-black tracking-tighter">BLINFERENCE</span>
          </div>

          <nav className="flex items-center gap-1">
            <NavItem id="home" label="Home" />
            <NavItem id="marketplace" label="Market" />
            <NavItem id="inference" label="Portal" />
            <NavItem id="lab" label="Lab" />
          </nav>

          <div className="flex items-center gap-2 pl-4 pr-2">
            {address && !isRegistrationNeeded ? (
              <button 
                onClick={disconnect}
                className="flex items-center gap-2 px-4 py-1.5 bg-white/5 hover:bg-white/10 rounded-full border border-white/10 transition-all"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]" />
                <span className="text-[10px] font-mono">{address.substring(0, 6)}...</span>
                {role && <span className="ml-2 px-2 py-0.5 rounded-full bg-white/10 text-[9px] uppercase font-bold text-[var(--accent-cyan)]">{role}</span>}
              </button>
            ) : (
              <button 
                onClick={connect}
                disabled={isConnecting}
                className="bg-white text-black px-5 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-widest hover:bg-[var(--accent-cyan)] transition-colors disabled:opacity-50"
              >
                {isConnecting ? 'Connecting...' : 'Connect'}
              </button>
            )}
          </div>
        </motion.header>
      </div>

      {/* Registration Modal */}
      <AnimatePresence>
        {isRegistrationNeeded && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
          >
            <motion.div 
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              className="bg-[var(--bg-secondary)] border border-white/10 p-8 rounded-3xl max-w-md w-full shadow-2xl relative"
            >
              <button 
                onClick={() => disconnect()}
                className="absolute top-4 right-4 text-white/50 hover:text-white"
              >
                ✕
              </button>
              <div className="flex flex-col items-center mb-8">
                <div className="w-16 h-16 rounded-full bg-[var(--accent-cyan)]/10 flex items-center justify-center mb-4">
                  <Lock className="w-8 h-8 text-[var(--accent-cyan)]" />
                </div>
                <h2 className="text-2xl font-black tracking-tighter uppercase">New Wallet</h2>
                <p className="text-sm text-[var(--text-muted)] text-center mt-2">
                  Please select your role to continue registration.
                </p>
              </div>

              {authError && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-sm p-3 rounded-xl mb-6 text-center">
                  {authError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => register("client")}
                  disabled={isConnecting}
                  className="flex flex-col items-center justify-center p-6 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-[var(--accent-cyan)]/30 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group"
                >
                  <ShoppingBag className="w-8 h-8 text-white/60 group-hover:text-[var(--accent-cyan)] mb-3 transition-colors" />
                  <span className="font-bold text-sm">Client</span>
                  <span className="text-[10px] text-[var(--text-muted)] mt-1">Buy & Run AI</span>
                </button>
                
                <button
                  onClick={() => register("ai_lab")}
                  disabled={isConnecting}
                  className="flex flex-col items-center justify-center p-6 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-purple-500/30 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group"
                >
                  <Beaker className="w-8 h-8 text-white/60 group-hover:text-purple-400 mb-3 transition-colors" />
                  <span className="font-bold text-sm">AI LAB</span>
                  <span className="text-[10px] text-[var(--text-muted)] mt-1">Deploy Models</span>
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="pt-32 pb-24">
        <AnimatePresence mode="wait">
          {activeTab === 'home' && (
            <motion.div 
              key="home"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-7xl mx-auto px-6"
            >
              {/* Hero Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[70vh]">
                <div className="space-y-8">
                  <motion.div
                    initial={{ x: -50, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                  >
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent-cyan)]/10 border border-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] text-[10px] font-bold uppercase tracking-[0.2em] mb-6">
                      <div className="w-1 h-1 rounded-full bg-[var(--accent-cyan)] animate-ping" />
                      FHE-Powered Blind Inference
                    </div>
                    <h1 className="text-7xl font-black tracking-tighter leading-[0.9] uppercase">
                      The Largest <br />
                      <span className="neon-text">Blind AI</span> <br />
                      Marketplace
                    </h1>
                  </motion.div>
                  
                  <motion.p 
                    initial={{ x: -50, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="text-xl text-[var(--text-muted)] max-w-lg leading-relaxed"
                  >
                    Run machine learning models on encrypted data without ever revealing the plaintext. Secure, private, and decentralized.
                  </motion.p>

                  <motion.div 
                    initial={{ x: -50, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="flex gap-4"
                  >
                    <Button size="lg" onClick={() => setActiveTab('marketplace')}>
                      Explore Models <ArrowRight className="ml-2 w-4 h-4" />
                    </Button>
                    <Button variant="secondary" size="lg" onClick={() => setActiveTab('lab')}>
                      Lab Dashboard
                    </Button>
                  </motion.div>
                </div>

                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.5 }}
                >
                  <LayeredStack />
                </motion.div>
              </div>

              {/* Feature Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-32">
                {[
                  { title: 'Privacy First', desc: 'TFHE primitives ensure data remains encrypted throughout the entire compute lifecycle.', icon: Lock },
                  { title: 'Verifiable', desc: 'Every inference step is logged on the Fhenix ledger, providing a tamper-proof audit trail.', icon: Shield },
                  { title: 'Scalable', desc: 'Optimized for high-throughput blind inference across distributed compute nodes.', icon: Cpu },
                ].map((f, i) => (
                  <motion.div
                    key={i}
                    initial={{ y: 50, opacity: 0 }}
                    whileInView={{ y: 0, opacity: 1 }}
                    transition={{ delay: i * 0.1 }}
                    viewport={{ once: true }}
                    className="p-8 rounded-3xl bg-white/[0.02] border border-white/5 hover:border-[var(--accent-cyan)]/30 transition-all group"
                  >
                    <f.icon className="w-10 h-10 text-[var(--accent-cyan)] mb-6 group-hover:scale-110 transition-transform" />
                    <h3 className="text-xl font-bold mb-3">{f.title}</h3>
                    <p className="text-sm text-[var(--text-muted)] leading-relaxed">{f.desc}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'marketplace' && (
            <div className="max-w-7xl mx-auto px-6">
              <Marketplace onSelectLab={handleSelectLab} />
            </div>
          )}

          {activeTab === 'dataset_upload' && (
            <div className="max-w-7xl mx-auto px-6">
              {selectedLabAddress ? (
                <DatasetUpload labAddress={selectedLabAddress} onBack={() => setActiveTab('marketplace')} />
              ) : (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                  <h2 className="text-2xl font-bold">No AI Lab Selected</h2>
                  <Button onClick={() => setActiveTab('marketplace')} className="mt-6">Go to Marketplace</Button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'inference' && (
            <div className="max-w-7xl mx-auto px-6">
              {selectedModel ? (
                <InferencePortal model={selectedModel} />
              ) : (
                <div className="flex flex-col items-center justify-center py-24 space-y-6 text-center">
                  <ShoppingBag className="w-16 h-16 text-white/10" />
                  <h2 className="text-2xl font-bold">No Model Selected</h2>
                  <Button onClick={() => setActiveTab('marketplace')}>Go to Marketplace</Button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'lab' && (
            <div className="max-w-7xl mx-auto px-6">
              <LabDashboard />
            </div>
          )}
        </AnimatePresence>
      </main>

      {/* High-Fidelity Footer */}
      <footer className="relative mt-32 border-t border-white/5 bg-[var(--bg-secondary)] overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[300px] bg-[var(--accent-cyan)]/5 blur-[120px] rounded-full" />
        
        <div className="max-w-7xl mx-auto px-6 py-24 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 mb-24">
            <div className="space-y-8">
              <div className="flex items-center gap-3">
                <Shield className="w-8 h-8 text-[var(--accent-cyan)]" />
                <span className="text-2xl font-black tracking-tighter">BLINFERENCE</span>
              </div>
              <p className="text-xl text-[var(--text-muted)] max-w-md">
                Building the foundational layer for private, secure, and decentralized artificial intelligence.
              </p>
              <div className="flex gap-4">
                {[Github, Twitter, MessageSquare].map((Icon, i) => (
                  <a key={i} href="#" className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center hover:bg-[var(--accent-cyan)] hover:text-black transition-all">
                    <Icon className="w-5 h-5" />
                  </a>
                ))}
              </div>
            </div>

            <div className="space-y-8">
              <h3 className="text-lg font-bold">Sign up for our newsletter</h3>
              <div className="flex gap-2">
                <input 
                  type="email" 
                  placeholder="Your Email" 
                  className="flex-1 bg-white/5 border border-white/10 rounded-full px-6 py-3 text-sm focus:outline-none focus:border-[var(--accent-cyan)] transition-colors"
                />
                <button className="bg-white text-black px-8 py-3 rounded-full text-sm font-bold hover:bg-[var(--accent-cyan)] transition-colors">
                  Subscribe
                </button>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Stay updated with the latest FHE research and protocol updates.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-12 pt-12 border-t border-white/5">
            {[
              { title: 'Develop', links: ['Testnet', 'Faucet', 'Docs', 'Storage Scan'] },
              { title: 'Learn', links: ['Blog', 'AMAs', 'FAQs', 'Whitepaper'] },
              { title: 'Ecosystem', links: ['Accelerator', 'Press', 'Contact Us', 'Brand Kit'] },
              { title: 'Legal', links: ['Privacy Policy', 'Terms of Service', 'Cookie Policy'] },
            ].map((col, i) => (
              <div key={i} className="space-y-4">
                <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map((link, j) => (
                    <li key={j}>
                      <a href="#" className="text-sm text-[var(--text-muted)] hover:text-white transition-colors">{link}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-24 pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-[10px] font-bold text-white/20 uppercase tracking-[0.3em]">
              &copy; 2026 BLINFERENCE PROTOCOL // ZERO KNOWLEDGE AI
            </div>
            <div className="flex items-center gap-2 text-[10px] font-bold text-white/20 uppercase tracking-[0.3em]">
              <div className="w-1 h-1 rounded-full bg-[var(--status-success)]" />
              All Systems Operational
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
