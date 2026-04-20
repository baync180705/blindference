import { CheckCircle2, CircleDashed, Clock, XCircle } from 'lucide-react';
import { truncateAddress } from '../utils/helpers';
import { cn } from '../utils/helpers';

interface NodeInfo {
  address: string;
  status: string;
  stake?: number;
  reputationScore?: number;
}

interface VerdictInfo {
  address: string;
  verdict: 'CONFIRM' | 'REJECT' | null;
  confidence: number;
  stake?: number;
  reputationScore?: number;
}

interface QuorumVisualizerProps {
  leader?: NodeInfo;
  verifiers?: VerdictInfo[];
  status: string;
}

function RepBadge({ rep }: { rep?: number }) {
  if (rep === undefined) return null;
  const color = rep > 80 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : rep > 50 ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20';
  return (
     <span className={`text-[9px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded border ${color}`}>Rep: {rep}%</span>
  )
}

export function QuorumVisualizer({ leader, verifiers, status }: QuorumVisualizerProps) {
  return (
    <div className="space-y-3">
      {leader && (
        <div className="flex items-center gap-4 p-4 border border-white/10 bg-white/[0.02] rounded-xl shadow-sm">
          <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500 font-bold text-xs uppercase tracking-wider border border-emerald-500/20">
            L
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-0.5">
               <span className="text-sm font-semibold text-white block">Leader Node</span>
               <RepBadge rep={leader.reputationScore} />
            </div>
            <span className="font-mono text-xs text-gray-400 flex items-center gap-2">
               {truncateAddress(leader.address)} 
               {leader.stake && <span className="opacity-60">• Stake: {leader.stake} GNK</span>}
            </span>
          </div>
          <StatusBadge status={leader.status} />
        </div>
      )}
      
      {verifiers?.map((v, i) => (
        <div key={i} className="flex items-center gap-4 p-4 border border-white/10 bg-white/[0.02] rounded-xl shadow-sm">
          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-gray-400 font-bold text-xs border border-white/10">
            V{i + 1}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-0.5">
               <span className="text-sm font-semibold text-white block">Verifier {i+1}</span>
               <RepBadge rep={v.reputationScore} />
            </div>
            <span className="font-mono text-xs text-gray-400 flex items-center gap-2">
               {truncateAddress(v.address)}
               {v.stake && <span className="opacity-60">• Stake: {v.stake} GNK</span>}
            </span>
          </div>
          {v.verdict === 'CONFIRM' ? (
            <div className="flex items-center gap-2 px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md text-[11px] font-bold tracking-widest uppercase">
              <CheckCircle2 className="w-3.5 h-3.5" />
              CONFIRM
            </div>
          ) : v.verdict === 'REJECT' ? (
            <div className="flex items-center gap-2 px-2.5 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-md text-[11px] font-bold tracking-widest uppercase">
              <XCircle className="w-3.5 h-3.5" />
              REJECT
            </div>
          ) : (
            <div className="flex items-center gap-2 px-2.5 py-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded-md text-[11px] font-bold tracking-widest uppercase">
              <CircleDashed className="w-3.5 h-3.5 animate-spin" />
              WAITING
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isComplete = status === 'COMPLETE' || status === 'EXECUTED';
  return (
    <div className={cn(
      "px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest border",
        isComplete 
           ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" 
           : "bg-white/5 text-gray-400 border-white/10"
    )}>
      {status}
    </div>
  );
}
