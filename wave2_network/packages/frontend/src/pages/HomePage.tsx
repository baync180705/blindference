import { Link } from 'react-router-dom';
import { ArrowRight, Lock, Shield, Cpu } from 'lucide-react';

export function HomePage() {
  return (
    <div className="flex flex-col items-center pt-16 pb-12">
      <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-500 rounded border border-emerald-500/20 text-[10px] font-bold uppercase tracking-widest mb-8">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        Live on Arbitrum Sepolia
      </div>
      
      <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-center text-white leading-tight max-w-3xl mb-6">
        Confidential AI Risk Scoring via <span className="text-emerald-500">FHE</span>
      </h1>
      
      <p className="text-lg text-gray-400 text-center max-w-2xl mb-10 leading-relaxed">
        Run verifiable machine learning models over encrypted data. Blindference ensures your applicant data is never exposed in plaintext, while guaranteeing execution via crypto-economic quorum.
      </p>
      
      <div className="flex items-center gap-4">
        <Link 
          to="/inference/new" 
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-black px-8 py-3 rounded font-bold transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] text-sm group uppercase tracking-widest"
        >
          New Inference Request
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24 w-full">
        <div className="flex flex-col items-center text-center p-6 bg-white/[0.02] rounded-xl border border-white/5">
           <div className="w-12 h-12 bg-white/[0.03] text-emerald-500 rounded-xl flex items-center justify-center mb-4 border border-white/10">
              <Lock className="w-6 h-6" />
           </div>
           <h3 className="text-lg font-bold text-white mb-2">FHE Encryption</h3>
           <p className="text-sm text-gray-500">Locally encrypt applicant features. Data is evaluated entirely in cipher space.</p>
        </div>
        <div className="flex flex-col items-center text-center p-6 bg-white/[0.02] rounded-xl border border-white/5">
           <div className="w-12 h-12 bg-white/[0.03] text-emerald-500 rounded-xl flex items-center justify-center mb-4 border border-white/10">
              <Shield className="w-6 h-6" />
           </div>
           <h3 className="text-lg font-bold text-white mb-2">Verifiable Quorum</h3>
           <p className="text-sm text-gray-500">Results are independently verified by node clusters enforced by slashing conditions.</p>
        </div>
        <div className="flex flex-col items-center text-center p-6 bg-white/[0.02] rounded-xl border border-white/5">
           <div className="w-12 h-12 bg-white/[0.03] text-emerald-500 rounded-xl flex items-center justify-center mb-4 border border-white/10">
              <Cpu className="w-6 h-6" />
           </div>
           <h3 className="text-lg font-bold text-white mb-2">Open Marketplace</h3>
           <p className="text-sm text-gray-500">Choose from top open-source models like Llama 3 70B or connect API endpoints like Gemini Pro.</p>
        </div>
      </div>
    </div>
  );
}
