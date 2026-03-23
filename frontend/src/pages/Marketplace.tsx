import { MOCK_MODELS, Model } from '../services/fheService';
import { Card, Button } from '../components/UI';
import { Database, Cpu, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';

export default function Marketplace({ onSelectModel }: { onSelectModel: (model: Model) => void }) {
  return (
    <div className="space-y-12">
      <div className="flex flex-col md:flex-row items-end justify-between gap-6">
        <div className="space-y-4">
          <div className="text-[10px] font-bold uppercase tracking-[0.4em] text-[var(--accent-cyan)]">Registry // v2.0</div>
          <h1 className="text-5xl font-black tracking-tighter uppercase">Model <span className="neon-text">Marketplace</span></h1>
          <p className="text-[var(--text-muted)] max-w-md">Securely browse and deploy FHE-ready inference models from top AI labs.</p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-3 px-6 py-3 bg-white/5 rounded-full border border-white/10">
            <Database className="w-4 h-4 text-[var(--accent-cyan)]" />
            <span className="text-xs font-mono font-bold">128 ACTIVE MODELS</span>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-5 px-8 py-4 text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">
          <div className="col-span-2">Model Identifier</div>
          <div>Price (FHERC20)</div>
          <div>Lab Address</div>
          <div className="text-right">Action</div>
        </div>

        {MOCK_MODELS.map((model, i) => (
          <motion.div
            key={model.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="grid grid-cols-5 items-center hover:bg-white/[0.04] transition-all py-6 group cursor-pointer">
              <div className="col-span-2 flex items-center gap-6">
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-[var(--accent-cyan)]/50 transition-colors">
                  <Cpu className="w-6 h-6 text-[var(--accent-cyan)]" />
                </div>
                <div>
                  <div className="font-bold text-lg group-hover:text-[var(--accent-cyan)] transition-colors">{model.name}</div>
                  <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest">{model.id}</div>
                </div>
              </div>
              <div className="font-mono text-[var(--accent-cyan)] font-bold">{model.price} FHE</div>
              <div className="text-[10px] font-mono text-white/40 uppercase tracking-widest">{model.labAddress}</div>
              <div className="text-right">
                <Button variant="outline" size="sm" onClick={() => onSelectModel(model)}>
                  Select <ArrowRight className="ml-2 w-3 h-3" />
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
