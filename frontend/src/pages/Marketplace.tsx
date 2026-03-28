import { useState, useEffect } from 'react';
import { Card, Button } from '../components/UI';
import { Database, Beaker, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { getAILabs } from '../services/apiService';

export default function Marketplace({ onSelectLab }: { onSelectLab: (address: string) => void }) {
  const [labs, setLabs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAILabs()
      .then(data => {
        setLabs(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-12">
      <div className="flex flex-col md:flex-row items-end justify-between gap-6">
        <div className="space-y-4">
          <div className="text-[10px] font-bold uppercase tracking-[0.4em] text-[var(--accent-cyan)]">Registry // v2.0</div>
          <h1 className="text-5xl font-black tracking-tighter uppercase">AI Lab <span className="neon-text">Marketplace</span></h1>
          <p className="text-[var(--text-muted)] max-w-md">Securely browse registered AI Labs and push encrypted datasets for blind inference.</p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-3 px-6 py-3 bg-white/5 rounded-full border border-white/10">
            <Database className="w-4 h-4 text-[var(--accent-cyan)]" />
            <span className="text-xs font-mono font-bold">{labs.length} ACTIVE LABS</span>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-4 px-8 py-4 text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">
          <div className="col-span-2">Lab Address</div>
          <div>Joined Date</div>
          <div className="text-right">Action</div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-white/50 font-mono text-sm">LOADING LABS...</div>
        ) : labs.map((lab, i) => (
          <motion.div
            key={lab.address}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="grid grid-cols-4 items-center hover:bg-white/[0.04] transition-all py-6 group cursor-pointer">
              <div className="col-span-2 flex items-center gap-6">
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-purple-500/50 transition-colors">
                  <Beaker className="w-6 h-6 text-purple-400 group-hover:text-purple-300 transition-colors" />
                </div>
                <div>
                  <div className="font-mono font-bold text-lg group-hover:text-purple-400 transition-colors">{lab.address.substring(0, 10)}...{lab.address.substring(lab.address.length - 8)}</div>
                  <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mt-1">AI LAB INSTANCE</div>
                </div>
              </div>
              <div className="text-xs font-mono text-white/40">{lab.created_at ? new Date(lab.created_at).toLocaleDateString() : 'N/A'}</div>
              <div className="text-right">
                <Button variant="outline" size="sm" onClick={() => onSelectLab(lab.address)}>
                  Upload Dataset <ArrowRight className="ml-2 w-3 h-3" />
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
        {!loading && labs.length === 0 && (
          <div className="text-center py-12 text-white/50 font-mono text-sm border border-white/10 rounded-2xl border-dashed">
            NO AI LABS REGISTERED YET. SIGN UP AS AN AI LAB TO APPEAR HERE.
          </div>
        )}
      </div>
    </div>
  );
}
