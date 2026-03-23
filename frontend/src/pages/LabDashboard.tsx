import React, { useState, FormEvent, useRef } from 'react';
import { Card, Button, Input } from '../components/UI';
import { Beaker, Upload, DollarSign, Info, CheckCircle, FileJson, FileCode, CheckCircle2, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { WeightParserService, ParsedWeights } from '../services/WeightParserService';
import { encrypt_uint32 } from '../services/fheService';

export default function LabDashboard() {
  const [price, setPrice] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  
  // New state for file upload
  const [parsedData, setParsedData] = useState<ParsedWeights | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [encryptionProgress, setEncryptionProgress] = useState<{ current: number, total: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsParsing(true);
    try {
      const result = await WeightParserService.parse(file);
      setParsedData(result);
    } catch (error) {
      console.error("Parsing failed:", error);
      alert(error instanceof Error ? error.message : "Failed to parse file");
    } finally {
      setIsParsing(false);
    }
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    if (!parsedData) return;

    setIsRegistering(true);
    
    try {
      // Encryption Pipeline
      const total = parsedData.weights.length;
      setEncryptionProgress({ current: 0, total });
      
      const encryptedWeights: string[] = [];
      for (let i = 0; i < total; i++) {
        const enc = await encrypt_uint32(parsedData.weights[i]);
        encryptedWeights.push(enc);
        if (i % 10 === 0 || i === total - 1) {
          setEncryptionProgress({ current: i + 1, total });
        }
      }

      console.log("Encrypted weights ready for transaction:", encryptedWeights.length);
      
      // Mock registerModel transaction
      await new globalThis.Promise(resolve => setTimeout(resolve, 1500));
      
      setIsSuccess(true);
      setParsedData(null);
      setPrice('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      setTimeout(() => setIsSuccess(false), 5000);
    } catch (error) {
      console.error("Registration failed:", error);
    } finally {
      setIsRegistering(false);
      setEncryptionProgress(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-[var(--accent-cyan)]/10 rounded-xl">
          <Beaker className="w-8 h-8 text-[var(--accent-cyan)]" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight neon-text">Lab Dashboard</h1>
          <p className="text-[var(--text-muted)]">Register your quantized ML models for blind inference.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <Card>
            <form onSubmit={handleRegister} className="space-y-8">
              {/* Model Upload Zone */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                  <Upload className="w-4 h-4" />
                  Model Weight Ingestion
                </div>
                
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="group relative border-2 border-dashed border-white/10 rounded-2xl p-12 text-center hover:border-[var(--accent-cyan)]/50 transition-all cursor-pointer bg-white/[0.01]"
                >
                  <input 
                    type="file" 
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".json,.proto,.bin"
                    className="hidden"
                  />
                  
                  <AnimatePresence mode="wait">
                    {isParsing ? (
                      <motion.div 
                        key="parsing"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="flex flex-col items-center gap-4"
                      >
                        <Loader2 className="w-12 h-12 text-[var(--accent-cyan)] animate-spin" />
                        <p className="text-sm font-mono text-[var(--accent-cyan)]">Analyzing schema...</p>
                      </motion.div>
                    ) : parsedData ? (
                      <motion.div 
                        key="parsed"
                        initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                        className="flex flex-col items-center gap-4"
                      >
                        <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                          <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                        </div>
                        <div>
                          <p className="text-lg font-bold text-emerald-500">Schema Validated</p>
                          <p className="text-sm text-[var(--text-muted)] mt-1">
                            Detected {parsedData.count.toLocaleString()} weights in {parsedData.format.toUpperCase()} format
                          </p>
                        </div>
                        <Button variant="secondary" size="sm" onClick={(e) => { e.stopPropagation(); setParsedData(null); }}>
                          Change File
                        </Button>
                      </motion.div>
                    ) : (
                      <motion.div 
                        key="idle"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        className="space-y-4"
                      >
                        <div className="flex justify-center gap-4">
                          <FileJson className="w-10 h-10 text-white/20 group-hover:text-[var(--accent-cyan)] transition-colors" />
                          <FileCode className="w-10 h-10 text-white/20 group-hover:text-[var(--accent-cyan)] transition-colors" />
                        </div>
                        <div>
                          <p className="text-lg font-bold">Drop model weights here</p>
                          <p className="text-sm text-[var(--text-muted)] mt-1">Supports .json, .proto, and .bin formats</p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              <div className="space-y-4 pt-6 border-t border-white/5">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                  <DollarSign className="w-4 h-4" />
                  Marketplace Configuration
                </div>
                <div className="max-w-xs">
                  <Input label="Query Price (FHERC20)" type="number" step="0.1" placeholder="5.0" value={price} onChange={e => setPrice(e.target.value)} required />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                    <Info className="w-3 h-3" />
                    Weights are encrypted before storage on-chain
                  </div>
                  {encryptionProgress && (
                    <div className="text-[10px] font-mono text-[var(--accent-cyan)]">
                      Encrypting: {encryptionProgress.current} / {encryptionProgress.total}
                    </div>
                  )}
                </div>
                <Button type="submit" isLoading={isRegistering} disabled={!parsedData}>
                  {encryptionProgress ? 'Encrypting...' : 'Encrypt & Register'}
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-[var(--bg-secondary)]/30 border-dashed">
            <h3 className="text-xs font-bold uppercase tracking-widest mb-4 text-[var(--text-muted)]">Quantization Guide</h3>
            <div className="space-y-4 text-xs text-[var(--text-muted)] leading-relaxed">
              <p>FHE arithmetic works best with integers. Please ensure your weights are scaled (e.g., x1000) and quantized to 8-bit or 16-bit signed integers.</p>
              <div className="p-3 bg-[var(--bg-secondary)] rounded border border-[var(--bg-secondary)] font-mono">
                f(x) = round(w * x + b)
              </div>
              <p>The Fhenix network will execute this linear combination blindly using TFHE primitives.</p>
            </div>
          </Card>

          <AnimatePresence>
            {isSuccess && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start gap-3"
              >
                <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
                <div>
                  <div className="text-sm font-bold text-emerald-500">Registration Success</div>
                  <div className="text-[10px] text-emerald-500/70">Model has been encrypted and deployed to the registry.</div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
