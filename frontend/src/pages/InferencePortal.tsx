import React, { useState, useEffect, useRef, FormEvent } from 'react';
import { Model, mockEncrypt, mockSubmitToChain, mockDecrypt } from '../services/fheService';
import { Card, Button, Input } from '../components/UI';
import { motion, AnimatePresence } from 'motion/react';
import { Shield, Terminal, Lock, Unlock, Activity, CheckCircle2 } from 'lucide-react';

export default function InferencePortal({ model }: { model: Model }) {
  const [biomarkers, setBiomarkers] = useState({
    age: '', glucose: '', bp: '', bmi: '', insulin: ''
  });
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<'idle' | 'encrypting' | 'computing' | 'sealed' | 'decrypting' | 'complete'>('idle');
  const [sealedHandle, setSealedHandle] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const addLog = (msg: string) => {
    setLogs(prev => [...prev, `[${new globalThis.Date().toLocaleTimeString()}] ${msg}`]);
  };

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleInference = async (e: FormEvent) => {
    e.preventDefault();
    setStatus('encrypting');
    setLogs([]);
    addLog(`Initiating blind inference with ${model.name}...`);
    
    try {
      const ciphertext = await mockEncrypt(biomarkers, addLog);
      setStatus('computing');
      const handle = await mockSubmitToChain(ciphertext, addLog);
      setSealedHandle(handle);
      setStatus('sealed');
    } catch (err) {
      addLog("ERROR: Inference failed.");
      setStatus('idle');
    }
  };

  const handleDecrypt = async () => {
    setStatus('decrypting');
    addLog("Requesting decryption from FHE gateway...");
    const res = await mockDecrypt(sealedHandle!);
    setResult(res);
    setStatus('complete');
    addLog(`Decryption successful. Result: ${res}`);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in fade-in duration-500">
      <div className="lg:col-span-2 space-y-6">
        <div className="flex items-center gap-4 mb-8">
          <div className="p-3 bg-[var(--accent-cyan)]/10 rounded-xl">
            <Shield className="w-8 h-8 text-[var(--accent-cyan)]" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight neon-text">Inference Portal</h1>
            <p className="text-[var(--text-muted)]">Securely process medical data using {model.name}.</p>
          </div>
        </div>

        <Card className="relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4">
             <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 rounded-full border border-emerald-500/20">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">Local Privacy Guard Active</span>
             </div>
          </div>

          <form onSubmit={handleInference} className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <Input label="Patient Age" type="number" placeholder="e.g. 45" value={biomarkers.age} onChange={e => setBiomarkers({...biomarkers, age: e.target.value})} required disabled={status !== 'idle'} />
              <Input label="Glucose Level" type="number" placeholder="mg/dL" value={biomarkers.glucose} onChange={e => setBiomarkers({...biomarkers, glucose: e.target.value})} required disabled={status !== 'idle'} />
              <Input label="Blood Pressure" type="number" placeholder="mmHg" value={biomarkers.bp} onChange={e => setBiomarkers({...biomarkers, bp: e.target.value})} required disabled={status !== 'idle'} />
              <Input label="BMI Index" type="number" step="0.1" placeholder="kg/m²" value={biomarkers.bmi} onChange={e => setBiomarkers({...biomarkers, bmi: e.target.value})} required disabled={status !== 'idle'} />
              <div className="col-span-2">
                <Input label="Insulin Level" type="number" placeholder="mu U/ml" value={biomarkers.insulin} onChange={e => setBiomarkers({...biomarkers, insulin: e.target.value})} required disabled={status !== 'idle'} />
              </div>
            </div>

            <div className="pt-4 flex items-center justify-between border-t border-[var(--bg-secondary)]">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                <Lock className="w-3 h-3" />
                No plaintext data ever leaves the browser
              </div>
              <Button type="submit" isLoading={status === 'encrypting' || status === 'computing'} disabled={status !== 'idle'}>
                Run Blind Inference
              </Button>
            </div>
          </form>
        </Card>

        <AnimatePresence>
          {status === 'computing' && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-12 space-y-4"
            >
              <motion.div 
                animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ repeat: Infinity, duration: 2 }}
                className="w-24 h-24 rounded-full border-4 border-[var(--accent-cyan)] flex items-center justify-center"
              >
                <Activity className="w-12 h-12 text-[var(--accent-cyan)]" />
              </motion.div>
              <h3 className="text-xl font-bold neon-text">On-Chain Computation</h3>
              <p className="text-sm text-[var(--text-muted)]">Executing FHE.mul/add arithmetic on encrypted ciphertext...</p>
            </motion.div>
          )}

          {(sealedHandle || result) && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-4"
            >
              <Card className="bg-[var(--bg-secondary)]/50 border-[var(--accent-cyan)]/30">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[var(--status-success)]" />
                    <h3 className="font-bold">Inference Result Generated</h3>
                  </div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">HANDLE: {sealedHandle?.substring(0, 12)}...</div>
                </div>

                {!result ? (
                  <div className="flex flex-col items-center py-6 space-y-4">
                    <div className="p-4 bg-[var(--bg-secondary)] rounded-lg border border-slate-800 w-full font-mono text-xs break-all text-[var(--text-muted)]">
                      {sealedHandle}
                    </div>
                    <Button variant="outline" onClick={handleDecrypt} isLoading={status === 'decrypting'}>
                      <Unlock className="w-4 h-4 mr-2" />
                      Decrypt Diagnosis
                    </Button>
                  </div>
                ) : (
                  <div className="text-center py-8 space-y-2">
                    <div className="text-sm uppercase tracking-widest text-[var(--text-muted)] font-bold">Final Diagnosis</div>
                    <div className="text-4xl font-black neon-text uppercase tracking-tighter">{result}</div>
                  </div>
                )}
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="space-y-6">
        <Card className="h-full flex flex-col min-h-[500px]">
          <div className="flex items-center gap-2 mb-4 border-b border-[var(--bg-secondary)] pb-4">
            <Terminal className="w-4 h-4 text-[var(--accent-cyan)]" />
            <h3 className="text-xs font-bold uppercase tracking-widest">Live Privacy Ledger</h3>
          </div>
          <div className="flex-1 overflow-y-auto space-y-2 font-mono text-[10px]">
            {logs.length === 0 && (
              <div className="text-[var(--text-muted)] italic opacity-50">Waiting for process initiation...</div>
            )}
            {logs.map((log, i) => (
              <div key={i} className="text-[var(--text-muted)] border-l-2 border-[var(--bg-secondary)] pl-2 py-1">
                {log}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </Card>
      </div>
    </div>
  );
}
