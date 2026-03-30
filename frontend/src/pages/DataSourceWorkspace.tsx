import { FormEvent, useEffect, useState } from 'react';
import { Card, Button, Input } from '../components/UI';
import { useWeb3 } from '../hooks/useWeb3';
import type { Model } from '../services/fheService';
import {
  createDatasetManifest,
  getOutgoingDatasets,
  getOutgoingSubmissions,
  type DatasetManifest,
  type SubmissionRecord,
  uploadEncryptedDataset,
} from '../services/workspaceService';
import { Database, FileUp, Loader2, ShieldAlert, ShieldCheck, Upload, Activity } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

export default function DataSourceWorkspace({ selectedModel }: { selectedModel: Model | null }) {
  const { address, role, jwt } = useWeb3();
  const [labAddress, setLabAddress] = useState(selectedModel?.labAddress ?? '');
  const [modelId, setModelId] = useState(selectedModel?.modelId?.toString() ?? '');
  const [notes, setNotes] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [submissions, setSubmissions] = useState<SubmissionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setLabAddress(selectedModel?.labAddress ?? '');
    setModelId(selectedModel?.modelId?.toString() ?? '');
  }, [selectedModel?.labAddress, selectedModel?.modelId]);

  useEffect(() => {
    if (!address || !jwt || role !== 'data_source') {
      return;
    }

    let isActive = true;

    async function loadWorkspace() {
      setIsLoading(true);
      try {
        const [nextDatasets, nextSubmissions] = await Promise.all([
          getOutgoingDatasets(address, jwt),
          getOutgoingSubmissions(address, jwt),
        ]);

        if (!isActive) {
          return;
        }

        setDatasets(nextDatasets);
        setSubmissions(nextSubmissions);
      } catch (loadError) {
        if (!isActive) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load Data Source workspace');
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
  }, [address, jwt, role]);

  if (role !== 'data_source') {
    return (
      <div className="mx-auto flex max-w-3xl flex-col items-center justify-center py-24 text-center">
        <div className="mb-6 rounded-full border border-rose-500/20 bg-rose-500/10 p-5">
          <ShieldAlert className="h-10 w-10 text-rose-300" />
        </div>
        <h1 className="text-3xl font-black uppercase tracking-tight text-rose-200">Data Source Access Only</h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
          This workspace is reserved for Data Source wallets. Use it to upload encrypted datasets, monitor orchestration metadata, and track private inference requests.
        </p>
      </div>
    );
  }

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!address || !jwt) {
      setError('Authenticate your wallet before uploading datasets.');
      return;
    }
    if (!file) {
      setError('Select a dataset file before uploading.');
      return;
    }
    if (labAddress.trim() === '') {
      setError('Provide the AI Lab wallet that should receive this dataset.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadSuccess(null);

    try {
      const uploadResult = await uploadEncryptedDataset(file);
      const manifest = await createDatasetManifest(jwt, {
        file_id: uploadResult.file_id,
        filename: file.name,
        lab_address: labAddress,
        model_id: modelId || undefined,
        content_type: file.type || 'application/octet-stream',
        notes,
      });

      setDatasets((prev) => [manifest, ...prev]);
      setFile(null);
      setNotes('');
      setUploadSuccess(`Dataset uploaded and assigned to ${manifest.lab_address}.`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Failed to upload dataset.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <div className="rounded-xl bg-[var(--accent-cyan)]/10 p-3">
          <Database className="h-8 w-8 text-[var(--accent-cyan)]" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight neon-text">Data Source Workspace</h1>
          <p className="text-[var(--text-muted)]">
            Upload encrypted datasets, assign them to AI Labs, and track your blind inference activity.
          </p>
        </div>
      </div>

      <div className="grid gap-8 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card>
            <form onSubmit={handleUpload} className="space-y-6">
              <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                <Upload className="h-4 w-4" />
                Dataset Intake
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <Input
                  label="AI Lab Wallet"
                  type="text"
                  value={labAddress}
                  onChange={(event) => setLabAddress(event.target.value)}
                  placeholder="0x..."
                  required
                />
                <Input
                  label="Model ID"
                  type="text"
                  value={modelId}
                  onChange={(event) => setModelId(event.target.value)}
                  placeholder="Optional on-chain model id"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                  Notes
                </label>
                <textarea
                  className="min-h-28 w-full rounded-3xl border border-white/10 bg-white/5 px-6 py-4 text-sm text-white focus:border-[var(--accent-cyan)] focus:outline-none"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Optional metadata about this upload, expected schema, or purpose."
                />
              </div>

              <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.02] p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                      Dataset File
                    </div>
                    <div className="mt-2 text-sm text-[var(--text-muted)]">
                      Upload the encrypted or pre-packaged dataset artifact that should be orchestrated off-chain.
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
                  This uses Mongo/GridFS only as an orchestration layer for encrypted artifacts. AI Lab authority remains on-chain.
                </div>
                <Button type="submit" isLoading={isUploading}>
                  Upload Dataset
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-[var(--bg-secondary)]/30 border-dashed">
            <h3 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)]">Selected Model</h3>
            <div className="mt-4 space-y-2 text-sm">
              <div>{selectedModel?.name ?? 'No model preselected'}</div>
              <div className="text-[var(--text-muted)]">{selectedModel?.labAddress ?? 'Choose a model from the marketplace to prefill this form.'}</div>
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
                Loading workspace data...
              </motion.div>
            )}
            {uploadSuccess && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200"
              >
                <ShieldCheck className="mr-2 inline h-4 w-4" />
                {uploadSuccess}
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

      <div className="grid gap-8 xl:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
              Uploaded Datasets
            </div>
            <div className="text-xs font-mono text-white/40">{datasets.length} records</div>
          </div>

          <div className="mt-6 space-y-4">
            {datasets.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-[var(--text-muted)]">
                No datasets uploaded yet.
              </div>
            ) : (
              datasets.map((dataset) => (
                <div key={dataset.dataset_id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-bold">{dataset.filename}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">
                        Lab {dataset.lab_address} {dataset.model_id ? `// Model ${dataset.model_id}` : ''}
                      </div>
                    </div>
                    <div className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                      {dataset.status}
                    </div>
                  </div>
                  <div className="mt-4 text-xs font-mono text-white/40">
                    File ID {dataset.file_id}
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
              Inference Requests
            </div>
            <div className="text-xs font-mono text-white/40">{submissions.length} tracked</div>
          </div>

          <div className="mt-6 space-y-4">
            {submissions.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-[var(--text-muted)]">
                No inference requests tracked yet. Run blind inference from the marketplace flow to populate this list.
              </div>
            ) : (
              submissions.map((submission) => (
                <div key={submission.submission_id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-bold">Request {submission.request_id}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">
                        Model {submission.model_id} // Lab {submission.lab_address}
                      </div>
                    </div>
                    <div className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[var(--accent-cyan)]">
                      {submission.status}
                    </div>
                  </div>
                  {submission.plaintext_result && (
                    <div className="mt-4 flex items-center gap-2 text-sm text-emerald-300">
                      <Activity className="h-4 w-4" />
                      Result {submission.plaintext_result}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
