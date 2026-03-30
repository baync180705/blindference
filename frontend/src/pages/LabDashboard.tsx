import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { formatUnits } from 'ethers';
import { Card, Button, Input } from '../components/UI';
import { Beaker, DollarSign, Info, CheckCircle, CheckCircle2, Loader2, Shield, ShieldAlert, Sparkles, Wallet } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useWeb3 } from '../hooks/useWeb3';
import { createMockDiabetesModel, registerMockModel, toPriceUnits } from '../services/fheService';
import { getUserProfile } from '../services/profileService';
import { getIncomingDatasets, getIncomingSubmissions, type DatasetManifest, type SubmissionRecord } from '../services/workspaceService';

export default function LabDashboard() {
  const { address, role, jwt, connect, fhenixClient, ensureFhenixClient, contracts, isInitializingFhe } = useWeb3();
  const [price, setPrice] = useState('0');
  const [profileURI, setProfileURI] = useState('blindference://labs/demo-diabetes-lab');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isActivatingLab, setIsActivatingLab] = useState(false);
  const [isCheckingLabStatus, setIsCheckingLabStatus] = useState(false);
  const [isLabRegisteredOnChain, setIsLabRegisteredOnChain] = useState(false);
  const [labActivationTxHash, setLabActivationTxHash] = useState<string | null>(null);
  const [registeredModelId, setRegisteredModelId] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [incomingDatasets, setIncomingDatasets] = useState<DatasetManifest[]>([]);
  const [incomingSubmissions, setIncomingSubmissions] = useState<SubmissionRecord[]>([]);
  const [labModels, setLabModels] = useState<Array<{ modelId: bigint; name: string; fee: bigint; ipfsHash: string }>>([]);
  const [isLoadingOperations, setIsLoadingOperations] = useState(false);

  const mockModel = useMemo(() => createMockDiabetesModel(), []);

  useEffect(() => {
    if (!address || !jwt || role !== 'ai_lab') {
      return;
    }

    let isActive = true;

    async function hydrateProfile() {
      try {
        const profile = await getUserProfile(address, jwt);
        if (!isActive) {
          return;
        }

        if (profile.profile_uri) {
          setProfileURI(profile.profile_uri);
        } else {
          setProfileURI(`blindference://labs/${address.toLowerCase()}`);
        }
      } catch (loadError) {
        if (!isActive) {
          return;
        }
        console.error('Failed to load AI lab profile:', loadError);
        setProfileURI(`blindference://labs/${address.toLowerCase()}`);
      }
    }

    void hydrateProfile();

    return () => {
      isActive = false;
    };
  }, [address, jwt, role]);

  useEffect(() => {
    if (!address || role !== 'ai_lab' || !contracts.modelRegistry) {
      setIsLabRegisteredOnChain(false);
      return;
    }

    let isActive = true;

    async function loadLabStatus() {
      setIsCheckingLabStatus(true);
      try {
        const labRecord = await contracts.modelRegistry?.aiLabs(address);
        const onChainRegistered =
          typeof labRecord?.isRegistered === 'boolean'
            ? labRecord.isRegistered
            : Boolean(Array.isArray(labRecord) ? labRecord[1] : false);

        const onChainProfileUri =
          typeof labRecord?.profileURI === 'string'
            ? labRecord.profileURI
            : typeof labRecord?.[0] === 'string'
              ? labRecord[0]
              : '';

        if (!isActive) {
          return;
        }

        setIsLabRegisteredOnChain(onChainRegistered);
        if (onChainProfileUri) {
          setProfileURI(onChainProfileUri);
        }
      } catch (statusError) {
        if (!isActive) {
          return;
        }
        console.error('Failed to read on-chain AI lab status:', statusError);
      } finally {
        if (isActive) {
          setIsCheckingLabStatus(false);
        }
      }
    }

    void loadLabStatus();

    return () => {
      isActive = false;
    };
  }, [address, role, contracts.modelRegistry]);

  useEffect(() => {
    if (!address || !jwt || role !== 'ai_lab') {
      return;
    }

    let isActive = true;

    async function loadOperationsMetadata() {
      setIsLoadingOperations(true);
      try {
        const [datasets, submissions] = await Promise.all([
          getIncomingDatasets(address, jwt),
          getIncomingSubmissions(address, jwt),
        ]);

        if (!isActive) {
          return;
        }

        setIncomingDatasets(datasets);
        setIncomingSubmissions(submissions);
      } catch (operationsError) {
        if (!isActive) {
          return;
        }
        console.error('Failed to load incoming AI lab metadata:', operationsError);
      } finally {
        if (isActive) {
          setIsLoadingOperations(false);
        }
      }
    }

    void loadOperationsMetadata();

    return () => {
      isActive = false;
    };
  }, [address, jwt, role]);

  useEffect(() => {
    if (!address || role !== 'ai_lab' || !contracts.modelRegistry) {
      setLabModels([]);
      return;
    }

    let isActive = true;

    async function loadLabModels() {
      try {
        const modelCount = (await contracts.modelRegistry?.modelCount()) as bigint;
        const models: Array<{ modelId: bigint; name: string; fee: bigint; ipfsHash: string }> = [];

        for (let index = 1n; index <= modelCount; index += 1n) {
          try {
            const [labWallet, ipfsHash, fee] = await Promise.all([
              contracts.modelRegistry?.getLabWallet(index) as Promise<string>,
              contracts.modelRegistry?.getIpfsHash(index) as Promise<string>,
              contracts.modelRegistry?.getInferenceFee(index) as Promise<bigint>,
            ]);

            if (labWallet.toLowerCase() === address.toLowerCase()) {
              models.push({
                modelId: index,
                name: ipfsHash || `Encrypted Model #${index.toString()}`,
                fee,
                ipfsHash,
              });
            }
          } catch {
            continue;
          }
        }

        if (isActive) {
          setLabModels(models);
        }
      } catch (modelError) {
        if (isActive) {
          console.error('Failed to load AI lab models:', modelError);
        }
      }
    }

    void loadLabModels();

    return () => {
      isActive = false;
    };
  }, [address, role, contracts.modelRegistry, registeredModelId]);

  if (role !== 'ai_lab') {
    return (
      <div className="mx-auto flex max-w-3xl flex-col items-center justify-center py-24 text-center">
        <div className="mb-6 rounded-full border border-rose-500/20 bg-rose-500/10 p-5">
          <ShieldAlert className="h-10 w-10 text-rose-300" />
        </div>
        <h1 className="text-3xl font-black uppercase tracking-tight text-rose-200">AI Lab Access Only</h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
          The Lab Dashboard is the supply-side workspace for registered AI Labs. Choose the AI Lab role from the onboarding shell to manage profiles, register encrypted models, and set inference pricing.
        </p>
      </div>
    );
  }

  const handleActivateLab = async () => {
    setError(null);
    setLabActivationTxHash(null);
    setIsActivatingLab(true);

    try {
      let activeRegistry = contracts.modelRegistry;
      let activeAddress = address;

      if (!activeAddress) {
        const session = await connect();
        activeRegistry = session?.contracts.modelRegistry ?? activeRegistry;
        activeAddress = session?.address ?? activeAddress;
      }

      if (!activeRegistry) {
        throw new Error('ModelRegistry contract is not configured');
      }

      if (!activeAddress) {
        throw new Error('AI lab wallet is not connected');
      }

      const trimmedProfileUri = profileURI.trim();
      if (trimmedProfileUri === '') {
        throw new Error('AI lab profile URI is required before on-chain activation');
      }

      const labRecord = await activeRegistry.aiLabs(activeAddress);
      const alreadyRegistered =
        typeof labRecord?.isRegistered === 'boolean'
          ? labRecord.isRegistered
          : Boolean(Array.isArray(labRecord) ? labRecord[1] : false);

      if (!alreadyRegistered) {
        const activationTx = await activeRegistry.registerLab(trimmedProfileUri);
        const receipt = await activationTx.wait();
        setLabActivationTxHash(receipt?.hash ?? activationTx.hash ?? null);
      }

      setIsLabRegisteredOnChain(true);
    } catch (activationError) {
      setError(
        activationError instanceof Error
          ? activationError.message
          : 'Failed to activate AI lab on-chain.',
      );
    } finally {
      setIsActivatingLab(false);
    }
  };

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

      if (!isLabRegisteredOnChain) {
        throw new Error('Activate this AI Lab on-chain before registering models.');
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

      <Card className={isLabRegisteredOnChain ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-amber-500/20 bg-amber-500/5'}>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
              <Wallet className="h-4 w-4" />
              On-Chain AI Lab Activation
            </div>
            <h2 className="text-2xl font-black uppercase tracking-tight">
              {isLabRegisteredOnChain ? 'AI Lab Registered On Fhenix' : 'Activate Your AI Lab Identity'}
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
              Phase 4 treats the AI Lab role as canonical on-chain. Before listing models, this wallet must publish its lab identity through `ModelRegistry.registerLab(profileURI)`.
            </p>
            <div className="text-xs font-mono text-white/50">
              Wallet: {address ?? 'Disconnected'}
            </div>
            {labActivationTxHash && (
              <div className="text-xs font-mono text-emerald-300 break-all">
                Activation Tx: {labActivationTxHash}
              </div>
            )}
          </div>

          <div className="w-full max-w-xl space-y-4">
            <Input
              label="AI Lab Profile URI"
              type="text"
              value={profileURI}
              onChange={(event) => setProfileURI(event.target.value)}
              placeholder="blindference://labs/demo-diabetes-lab"
              disabled={isLabRegisteredOnChain || isActivatingLab}
              required
            />
            <div className="flex items-center justify-between gap-4">
              <div className="text-xs text-[var(--text-muted)]">
                {isCheckingLabStatus
                  ? 'Checking on-chain registration state...'
                  : isLabRegisteredOnChain
                    ? 'This wallet can now register encrypted models.'
                    : 'Complete this transaction once per AI Lab wallet.'}
              </div>
              <Button
                type="button"
                onClick={handleActivateLab}
                isLoading={isActivatingLab}
                disabled={isLabRegisteredOnChain || isCheckingLabStatus}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                {isLabRegisteredOnChain ? 'Activated' : 'Activate On-Chain'}
              </Button>
            </div>
          </div>
        </div>
      </Card>

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
                    disabled={isLabRegisteredOnChain}
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
                <Button type="submit" isLoading={isRegistering || isInitializingFhe} disabled={!isLabRegisteredOnChain}>
                  {isRegistering
                    ? 'Encrypting & Registering...'
                    : isInitializingFhe
                      ? 'Initializing FHE...'
                      : isLabRegisteredOnChain
                        ? 'Register Mock Model'
                        : 'Activate Lab First'}
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

      <div className="grid gap-8 xl:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
              Registered Models
            </div>
            <div className="text-xs font-mono text-white/40">{labModels.length} active</div>
          </div>

          <div className="mt-6 space-y-4">
            {labModels.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-[var(--text-muted)]">
                No models registered for this AI Lab wallet yet.
              </div>
            ) : (
              labModels.map((model) => (
                <div key={model.modelId.toString()} className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-bold">{model.name}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">Model ID {model.modelId.toString()}</div>
                    </div>
                    <div className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                      {formatUnits(model.fee, 18)} BFHE
                    </div>
                  </div>
                  <div className="mt-4 text-xs font-mono text-white/40">
                    {model.ipfsHash || 'No profile URI supplied'}
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
              Incoming Datasets
            </div>
            <div className="text-xs font-mono text-white/40">
              {isLoadingOperations ? 'syncing...' : `${incomingDatasets.length} manifests`}
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {incomingDatasets.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-[var(--text-muted)]">
                No incoming dataset manifests have been assigned to this AI Lab yet.
              </div>
            ) : (
              incomingDatasets.map((dataset) => (
                <div key={dataset.dataset_id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-bold">{dataset.filename}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">
                        Owner {dataset.owner_address} {dataset.model_id ? `// Model ${dataset.model_id}` : ''}
                      </div>
                    </div>
                    <div className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                      {dataset.status}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
            Incoming Inference Activity
          </div>
          <div className="text-xs font-mono text-white/40">
            {isLoadingOperations ? 'syncing...' : `${incomingSubmissions.length} requests`}
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {incomingSubmissions.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-[var(--text-muted)]">
              No inference requests have been mirrored to the AI Lab metadata queue yet.
            </div>
          ) : (
            incomingSubmissions.map((submission) => (
              <div key={submission.submission_id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-bold">Request {submission.request_id}</div>
                    <div className="mt-1 text-xs text-[var(--text-muted)]">
                      Data Source {submission.owner_address} // Model {submission.model_id}
                    </div>
                  </div>
                  <div className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                    {submission.status}
                  </div>
                </div>
                {submission.tx_hash && (
                  <div className="mt-4 text-xs font-mono text-white/40 break-all">
                    Tx {submission.tx_hash}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
