import Papa from 'papaparse';
import { initializeEncryption, encryptRow } from './encryptionService';
import { uploadDatasetChunk } from './apiService';

export interface ProcessCallbacks {
  onStatusChange: (status: 'idle' | 'encrypting' | 'uploading' | 'success') => void;
  onProgress: (progress: number) => void;
  onError: (error: Error) => void;
  onComplete: () => void;
}

export const processAndUploadDataset = async (
  file: File,
  address: string,
  labAddress: string,
  cryptoProvider: any,
  callbacks: ProcessCallbacks
) => {
  try {
    callbacks.onStatusChange('encrypting');
    callbacks.onProgress(5);

    await initializeEncryption(cryptoProvider);

    let chunkIndex = 0;
    let progress = 5;

    Papa.parse(file, {
      header: true,
      chunkSize: 1024 * 50, // 50KB chunks
      chunk: async (results, parser) => {
        parser.pause();

        if (results.data.length === 0) {
          parser.resume();
          return;
        }

        callbacks.onStatusChange('encrypting');
        const columns = results.meta.fields || [];
        const encryptedRows = [];

        for (const row of results.data) {
          if (!row || Object.keys(row).length === 0) continue;
          
          const encryptedRes = await encryptRow(row, columns);
          encryptedRows.push(encryptedRes);
        }

        callbacks.onStatusChange('uploading');
        const payload = {
          owner_address: address,
          lab_address: labAddress,
          filename: file.name,
          chunk_index: chunkIndex,
          columns: columns,
          encrypted_rows: encryptedRows
        };

        await uploadDatasetChunk(payload);

        chunkIndex++;
        progress = Math.min(95, progress + 10);
        callbacks.onProgress(progress);
        
        parser.resume();
      },
      complete: () => {
        callbacks.onStatusChange('success');
        callbacks.onProgress(100);
        callbacks.onComplete();
      },
      error: (err: any) => {
        callbacks.onError(new Error(err.message));
      }
    });

  } catch (err: any) {
    callbacks.onError(err);
  }
};
