import React, { FormEvent, useMemo, useState } from 'react';
import { Card, Button, Input } from '../components/UI';
import { Beaker, DollarSign, Info, CheckCircle, CheckCircle2, Loader2, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useWeb3 } from '../hooks/useWeb3';
import { createMockDiabetesModel, registerMockModel, toPriceUnits } from '../services/fheService';

export default function LabDashboard() {
  const { address, connect, fhenixClient, ensureFhenixClient, contracts, isInitializingFhe } = useWeb3();
  const [price, setPrice] = useState('0');
  const [profileURI, setProfileURI] = useState('blindference://labs/demo-diabetes-lab');
  const [isRegistering, setIsRegistering] = useState(false);
  const [registeredModelId, setRegisteredModelId] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mockModel = useMemo(() => createMockDiabetesModel(), []);

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setIsRegistering(true);
    setRegisteredModelId(null);
    setTxHash(null);
    setError(null);

    try {
      let activeClient = fhenixClient;
      let activeRegistry = contracts.modelRegistry;
      let activeAddress = address;

      if (!address) {
        const session = await connect();
        activeClient = session?.fhenixClient ?? activeClient;
        activeRegistry = session?.contracts.modelRegistry ?? activeRegistry;
        activeAddress = session?.address ?? activeAddress;
      }

      if (!activeClient) {
        activeClient = await ensureFhenixClient();
      }

      if (!activeRegistry) {
        throw new Error('ModelRegistry contract is not configured');
      }

      if (!activeAddress) {
        throw new Error('AI lab wallet is not connected');
      }

      const labRecord = await activeRegistry.aiLabs(activeAddress);
      const isRegistered =
        typeof labRecord?.isRegistered === 'boolean'
          ? labRecord.isRegistered
          : Boolean(Array.isArray(labRecord) ? labRecord[1] : false);

      if (!isRegistered) {
        const profile = profileURI.trim();
        if (profile === '') {
          throw new Error('AI lab profile URI is required');
        }

        const registerLabTx = await activeRegistry.registerLab(profile);
        await registerLabTx.wait();
      }

      const { modelId, receipt } = await registerMockModel({
        client: activeClient,
        modelRegistry: activeRegistry,
        pricePerQuery: toPriceUnits(price),
      });

      setRegisteredModelId(modelId.toString());
      setTxHash(receipt.hash);
    } catch (registrationError) {
      setError(
        registrationError instanceof Error
          ? registrationError.message
          : 'Failed to register encrypted model.',
      );
    } finally {
      setIsRegistering(false);
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
          <p className="text-[var(--text-muted)]">Encrypt and register a quantized logistic-regression model with the Fhenix network public key.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <Card>
            <form onSubmit={handleRegister} className="space-y-8">
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                  <Shield className="w-4 h-4" />
                  Mock Logistic Regression Model
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-lg font-bold">{mockModel.name}</p>
                      <p className="text-sm text-[var(--text-muted)]">Quantized linear model for diabetes-risk scoring.</p>
                    </div>
                    <div className="text-right text-xs font-mono text-[var(--text-muted)]">
                      <div>SCALE {mockModel.scale}</div>
                      <div>{mockModel.ipfsHash}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    {mockModel.features.map((feature, index) => (
                      <div key={`${feature || 'feature'}-${index}`} className="rounded-xl border border-white/10 bg-[var(--bg-secondary)]/40 p-4">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">{feature}</div>
                        <div className="mt-2 text-2xl font-black neon-text">{mockModel.weights[index]}</div>
                      </div>
                    ))}
                  </div>

                  <div className="rounded-xl border border-white/10 bg-[var(--bg-secondary)]/40 p-4">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">Bias</div>
                    <div className="mt-2 text-2xl font-black neon-text">{mockModel.bias}</div>
                  </div>
                </div>
              </div>

              <div className="space-y-4 pt-6 border-t border-white/5">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                  <DollarSign className="w-4 h-4" />
                  Marketplace Configuration
                </div>
                <div className="max-w-xl">
                  <Input
                    label="AI Lab Profile URI"
                    type="text"
                    placeholder="blindference://labs/demo-diabetes-lab"
                    value={profileURI}
                    onChange={(e) => setProfileURI(e.target.value)}
                    required
                  />
                </div>
                <div className="max-w-xs">
                  <Input
                    label="Query Price (FHERC20)"
                    type="number"
                    step="0.1"
                    placeholder="0.0"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                    <Info className="w-3 h-3" />
                    The lab encrypts weights with the Fhenix network public key before registration.
                  </div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">
                    Features: {mockModel.features.join(' / ')}
                  </div>
                </div>
                <Button type="submit" isLoading={isRegistering || isInitializingFhe}>
                  {isRegistering
                    ? 'Encrypting & Registering...'
                    : isInitializingFhe
                      ? 'Initializing FHE...'
                      : 'Register Mock Model'}
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-[var(--bg-secondary)]/30 border-dashed">
            <h3 className="text-xs font-bold uppercase tracking-widest mb-4 text-[var(--text-muted)]">Quantization Guide</h3>
            <div className="space-y-4 text-xs text-[var(--text-muted)] leading-relaxed">
              <p>Weights and bias are scaled by 1000, then encrypted as `euint32` inputs before the lab submits them on-chain.</p>
              <div className="p-3 bg-[var(--bg-secondary)] rounded border border-[var(--bg-secondary)] font-mono">
                score = 150*Glucose + 210*BMI + 55*Age + 500
              </div>
              <p>Because the contract stores encrypted handles, neither the hospital nor the public chain can read the raw model parameters.</p>
            </div>
          </Card>

          <AnimatePresence>
            {registeredModelId && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start gap-3"
              >
                <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
                <div>
                  <div className="text-sm font-bold text-emerald-500">Registration Success</div>
                  <div className="text-[10px] text-emerald-500/70">Model ID {registeredModelId}</div>
                  {txHash && <div className="text-[10px] break-all text-emerald-500/70">{txHash}</div>}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-lg"
              >
                <div className="flex items-center gap-2 text-sm font-bold text-rose-300">
                  <Loader2 className="w-4 h-4" />
                  Registration Failed
                </div>
                <div className="mt-2 text-[10px] text-rose-200/80">{error}</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
