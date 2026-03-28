import React, { useState } from 'react';
import { Card, Button } from '../components/UI';
import { UploadCloud, ShieldCheck, Database, FileKey, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useWeb3 } from '../hooks/useWeb3';
import { processAndUploadDataset } from '../services/datasetService';

export default function DatasetUpload({ labAddress, onBack }: { labAddress: string, onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'encrypting' | 'uploading' | 'success'>('idle');
  const [progress, setProgress] = useState(0);

  const { address } = useWeb3();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleProcess = () => {
    if (!file || !address) return;
    if (!(window as any).ethereum) {
      console.error("No crypto wallet found.");
      setStatus('idle');
      return;
    }

    processAndUploadDataset(
       file,
       address,
       labAddress,
       (window as any).ethereum,
       {
         onStatusChange: setStatus,
         onProgress: setProgress,
         onError: (err: Error) => {
           console.error(err);
           setStatus('idle');
         },
         onComplete: () => console.log("Dataset process complete.")
       }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="p-2 bg-white/5 hover:bg-white/10 rounded-full transition-colors border border-white/10">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-3xl font-black tracking-tighter uppercase">Provide <span className="neon-text">Dataset</span></h1>
          <p className="text-[var(--text-muted)] text-sm font-mono mt-1">Target Lab: {labAddress}</p>
        </div>
      </div>

      <Card className="max-w-xl p-8 mx-auto mt-12 bg-white/[0.02] border-white/5">
        <AnimatePresence mode='wait'>
          {status === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center py-12 text-center">
              <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center border border-dashed border-white/20 mb-6">
                <UploadCloud className="w-10 h-10 text-[var(--accent-cyan)]" />
              </div>
              <h3 className="text-xl font-bold mb-2">Upload your CSV</h3>
              <p className="text-sm text-[var(--text-muted)] mb-8">Data gets encrypted locally before ever leaving your device.</p>
              
              <input type="file" accept=".csv" onChange={handleFileChange} id="file-upload" className="hidden" />
              <div className="flex flex-col gap-4 w-full">
                <label htmlFor="file-upload" className="w-full flex items-center justify-center py-3 border border-dashed border-white/20 hover:border-[var(--accent-cyan)]/50 rounded-xl cursor-pointer bg-white/5 hover:bg-white/10 transition-colors">
                  <span className="text-sm font-bold">{file ? file.name : "Select CSV File"}</span>
                </label>
                
                <Button size="lg" disabled={!file} onClick={handleProcess} className="w-full">
                  <FileKey className="w-4 h-4 mr-2" /> Encrypt & Upload
                </Button>
              </div>
            </motion.div>
          )}

          {(status === 'encrypting' || status === 'uploading') && (
            <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center py-12 text-center">
              <div className="w-20 h-20 rounded-full bg-[var(--accent-cyan)]/10 flex items-center justify-center border border-[var(--accent-cyan)]/20 mb-6 relative">
                 <div className="absolute inset-0 rounded-full animate-ping bg-[var(--accent-cyan)]/20" />
                 {status === 'encrypting' ? <FileKey className="w-10 h-10 text-[var(--accent-cyan)] animate-pulse" /> : <Database className="w-10 h-10 text-[var(--accent-cyan)] animate-bounce" />}
              </div>
              <h3 className="text-xl font-bold mb-2">
                {status === 'encrypting' ? 'Performing FHE Encryption...' : 'Storing on Network...'}
              </h3>
              <p className="text-sm text-[var(--text-muted)] mb-8 max-w-sm">
                Generating TFHE keys and securing your dataset payloads prior to off-chain storage.
              </p>
              
              <div className="w-full bg-white/5 rounded-full h-2 mb-2 overflow-hidden">
                <div className="bg-[var(--accent-cyan)] h-full transition-all duration-300" style={{ width: `${progress}%` }} />
              </div>
              <div className="text-[10px] font-mono font-bold text-white/50 tracking-widest">{progress}% COMPLETE</div>
            </motion.div>
          )}

          {status === 'success' && (
            <motion.div key="success" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center py-12 text-center">
              <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center border border-green-500/20 mb-6">
                <ShieldCheck className="w-10 h-10 text-green-400" />
              </div>
              <h3 className="text-xl font-bold mb-2 text-green-400">Dataset Secured & Stored</h3>
              <p className="text-sm text-[var(--text-muted)] mb-8">Your data is now safely encrypted and bound to {labAddress.substring(0,8)}... for blind computation.</p>
              <Button onClick={onBack} variant="outline">Back to Market</Button>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </div>
  );
}
