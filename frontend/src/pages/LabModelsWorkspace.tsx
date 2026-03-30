import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Card, Button, Input } from '../components/UI';
import { useWeb3 } from '../hooks/useWeb3';
import {
  downloadDatasetArtifact,
  getDatasetCatalog,
  getLabModelArtifacts,
  type DatasetManifest,
  type TrainedModelRecord,
  uploadModelArtifact,
} from '../services/workspaceService';
import {
  Beaker,
  Download,
  FileUp,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

function truncateAddress(address: string) {
  return address.length > 14 ? `${address.slice(0, 10)}...${address.slice(-4)}` : address;
}

function shortHash(hash?: string | null) {
  if (!hash) {
    return 'Pending';
  }

  return `${hash.slice(0, 10)}...${hash.slice(-6)}`;
}

export default function LabModelsWorkspace({ initialDatasetId }: { initialDatasetId?: string | null }) {
  const { address, role, jwt } = useWeb3();
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [models, setModels] = useState<TrainedModelRecord[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [status, setStatus] = useState('uploaded');
  const [onChainModelId, setOnChainModelId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activeDownloadId, setActiveDownloadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!address || !jwt || role !== 'ai_lab') {
      return;
    }

    let isActive = true;

    async function loadWorkspace() {
      setIsLoading(true);
      setError(null);
      try {
        const [nextDatasets, nextModels] = await Promise.all([
          getDatasetCatalog(jwt),
          getLabModelArtifacts(address, jwt),
        ]);

        if (!isActive) {
          return;
        }

        setDatasets(nextDatasets);
        setModels(nextModels);
        if (nextDatasets.length > 0 && selectedDatasetId === '') {
          setSelectedDatasetId(nextDatasets[0].dataset_id);
        }
      } catch (loadError) {
        if (!isActive) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load model workspace');
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadWorkspace();

    return () => {
      isActive = false;
    };
  }, [address, jwt, role, selectedDatasetId]);

  useEffect(() => {
    if (initialDatasetId) {
      setSelectedDatasetId(initialDatasetId);
    }
  }, [initialDatasetId]);

  const datasetMap = useMemo(
    () => new Map(datasets.map((dataset) => [dataset.dataset_id, dataset])),
    [datasets],
  );

  if (role !== 'ai_lab') {
    return (
      <div className="mx-auto flex max-w-3xl flex-col items-center justify-center py-24 text-center">
        <div className="mb-6 rounded-full border border-rose-500/20 bg-rose-500/10 p-5">
          <ShieldAlert className="h-10 w-10 text-rose-300" />
        </div>
        <h1 className="text-3xl font-black uppercase tracking-tight text-rose-200">AI Lab Access Only</h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
          The models workspace is reserved for AI Lab wallets so they can publish encrypted model artifacts with explicit dataset lineage.
        </p>
      </div>
    );
  }

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!jwt) {
      setError('Authenticate your AI lab wallet before uploading a model.');
      return;
    }
    if (selectedDatasetId === '') {
      setError('Select the dataset used to train this model.');
      return;
    }
    if (!file) {
      setError('Choose the encrypted model artifact file before uploading.');
      return;
    }
    if (name.trim() === '') {
      setError('Provide a model name.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const record = await uploadModelArtifact(jwt, {
        file,
        dataset_id: selectedDatasetId,
        name,
        description,
        price_bfhe: price || undefined,
        status,
        on_chain_model_id: onChainModelId || undefined,
      });

      setModels((prev) => [record, ...prev]);
      setFile(null);
      setName('');
      setDescription('');
      setPrice('');
      setStatus('uploaded');
      setOnChainModelId('');
      setSuccess(`Uploaded ${record.name} and linked it to its training dataset.`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Failed to upload model artifact');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async (model: TrainedModelRecord) => {
    if (!jwt) {
      setError('Authenticate your AI lab wallet before downloading model artifacts.');
      return;
    }

    setActiveDownloadId(model.model_id);
    setError(null);
    setSuccess(null);

    try {
      await downloadDatasetArtifact(model.file_id, model.filename, jwt);
      setSuccess(`Downloaded ${model.filename}`);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : 'Failed to download model artifact');
    } finally {
      setActiveDownloadId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <div className="rounded-xl bg-[var(--accent-cyan)]/10 p-3">
          <Beaker className="h-8 w-8 text-[var(--accent-cyan)]" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight neon-text">Model Upload</h1>
          <p className="text-[var(--text-muted)]">
            Publish encrypted model artifacts and make their training provenance explicit by linking each upload to a dataset.
          </p>
        </div>
      </div>

      <div className="grid gap-8 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card>
            <form onSubmit={handleUpload} className="space-y-6">
              <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                <Sparkles className="h-4 w-4" />
                Encrypted Model Artifact
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                    Training Dataset
                  </label>
                  <select
                    value={selectedDatasetId}
                    onChange={(event) => setSelectedDatasetId(event.target.value)}
                    className="w-full rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm text-white focus:border-[var(--accent-cyan)] focus:outline-none"
                    required
                  >
                    <option value="" disabled>
                      Select dataset
                    </option>
                    {datasets.map((dataset) => (
                      <option key={dataset.dataset_id} value={dataset.dataset_id} className="bg-slate-900 text-white">
                        {(dataset.original_filename ?? dataset.filename)} | {dataset.row_count ?? 0} rows
                      </option>
                    ))}
                  </select>
                </div>

                <Input
                  label="Model Name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Encrypted Diabetes Risk Model"
                  required
                />

                <Input
                  label="Price (BFHE)"
                  type="text"
                  value={price}
                  onChange={(event) => setPrice(event.target.value)}
                  placeholder="0.5"
                />

                <Input
                  label="On-Chain Model ID"
                  type="text"
                  value={onChainModelId}
                  onChange={(event) => setOnChainModelId(event.target.value)}
                  placeholder="Optional"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                  Description
                </label>
                <textarea
                  className="min-h-28 w-full rounded-3xl border border-white/10 bg-white/5 px-6 py-4 text-sm text-white focus:border-[var(--accent-cyan)] focus:outline-none"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Summarize what this encrypted model predicts and what dataset it was trained from."
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                  Publish Status
                </label>
                <select
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  className="w-full rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm text-white focus:border-[var(--accent-cyan)] focus:outline-none"
                >
                  <option value="uploaded" className="bg-slate-900 text-white">Uploaded</option>
                  <option value="ready" className="bg-slate-900 text-white">Ready</option>
                  <option value="training_complete" className="bg-slate-900 text-white">Training Complete</option>
                </select>
              </div>

              <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.02] p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                      Encrypted Weights Artifact
                    </div>
                    <div className="mt-2 text-sm text-[var(--text-muted)]">
                      Upload the encrypted weight artifact produced by your PPML-compatible training flow. Linking a dataset is mandatory.
                    </div>
                  </div>
                  <label className="inline-flex cursor-pointer items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-bold uppercase tracking-widest text-white transition-colors hover:border-[var(--accent-cyan)]/40">
                    <FileUp className="mr-2 h-4 w-4" />
                    {file ? file.name : 'Choose File'}
                    <input
                      type="file"
                      className="hidden"
                      onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-white/5 pt-4">
                <div className="text-xs text-[var(--text-muted)]">
                  Every model upload is stored off-chain as an encrypted artifact and linked back to the training dataset for provenance.
                </div>
                <Button type="submit" isLoading={isUploading} disabled={datasets.length === 0}>
                  Upload Model
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-[var(--bg-secondary)]/30 border-dashed">
            <h3 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)]">Dataset Requirement</h3>
            <div className="mt-4 space-y-3 text-sm text-[var(--text-muted)]">
              <p>Each model must reference exactly one dataset in this Wave 1 flow.</p>
              <p>This provenance link lets the datasets workspace display which models were trained on each encrypted dataset.</p>
              <p>The same record can also carry an optional on-chain model id after registration.</p>
            </div>
          </Card>

          <AnimatePresence>
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-white/70"
              >
                <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                Loading model workspace...
              </motion.div>
            )}
            {success && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200"
              >
                <ShieldCheck className="mr-2 inline h-4 w-4" />
                {success}
              </motion.div>
            )}
            {error && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200"
              >
                <ShieldAlert className="mr-2 inline h-4 w-4" />
                {error}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
            Uploaded Models
          </div>
          <div className="text-xs font-mono text-white/40">{models.length} records</div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {models.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-[var(--text-muted)] md:col-span-2">
              No encrypted models uploaded yet.
            </div>
          ) : (
            models.map((model) => {
              const dataset = datasetMap.get(model.dataset_id);
              return (
                <div key={model.model_id} className="rounded-3xl border border-white/10 bg-white/[0.02] p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-bold text-white">{model.name}</div>
                      <div className="mt-1 text-xs uppercase tracking-widest text-[var(--accent-cyan)]">
                        {model.status}
                      </div>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      isLoading={activeDownloadId === model.model_id}
                      onClick={() => void handleDownload(model)}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download
                    </Button>
                  </div>

                  <div className="mt-4 text-sm text-[var(--text-muted)]">
                    {model.description ?? 'No model description provided.'}
                  </div>

                  <div className="mt-4 grid gap-2 text-xs text-white/45">
                    <div>Dataset {(dataset?.original_filename ?? dataset?.filename) ?? model.dataset_id}</div>
                    <div>Owner {truncateAddress(model.lab_address)}</div>
                    <div>SHA {shortHash(model.artifact_sha256)}</div>
                    <div>{model.price_bfhe ? `${model.price_bfhe} BFHE` : 'No price metadata'} {model.on_chain_model_id ? `// On-chain ${model.on_chain_model_id}` : ''}</div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>
    </div>
  );
}
