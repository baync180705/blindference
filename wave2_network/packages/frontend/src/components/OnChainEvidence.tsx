import { ExternalLink } from 'lucide-react';

interface OnChainEvidenceProps {
  taskId: string;
  resultCommitTx?: string;
  escrowCreationTx?: string;
  escrowReleaseTx?: string;
  coveragePurchaseTx?: string;
}

export function OnChainEvidence({ taskId, resultCommitTx, escrowCreationTx, escrowReleaseTx, coveragePurchaseTx }: OnChainEvidenceProps) {
  const renderTx = (label: string, txHash?: string) => {
    if (!txHash) return null;
    return (
      <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
         <span className="text-[11px] text-gray-500 font-bold uppercase tracking-widest">{label}</span>
         <a href={`https://sepolia.arbiscan.io/tx/${txHash}`} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 transition-colors">
            <span className="font-mono text-[11px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">{txHash.slice(0, 10)}...{txHash.slice(-4)}</span>
            <ExternalLink className="w-3 h-3 text-emerald-500/70" />
         </a>
      </div>
    );
  };

  return (
    <section className="bg-white/[0.02] border border-white/5 rounded-xl p-5 space-y-4">
      <h3 className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black">On-Chain Evidence</h3>
      <div className="flex flex-col">
        <div className="flex justify-between items-center py-2 border-b border-white/5">
           <span className="text-[11px] text-gray-500 font-bold uppercase tracking-widest">Task ID</span>
           <span className="font-mono text-[11px] text-gray-400 bg-white/5 px-1.5 py-0.5 rounded border border-white/10">{taskId.slice(0, 16)}...</span>
        </div>
        {renderTx('Coverage Plan', coveragePurchaseTx)}
        {renderTx('Escrow Created', escrowCreationTx)}
        {renderTx('Result Commitment', resultCommitTx)}
        {renderTx('Escrow Released', escrowReleaseTx)}
      </div>
    </section>
  );
}
