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
  console.log("[datasetService] Starting processAndUploadDataset...");
  console.log(`[datasetService] File: ${file.name}, size: ${file.size} bytes`);
  
  try {
    callbacks.onStatusChange('encrypting');
    callbacks.onProgress(0);

    console.log("[datasetService] Initializing encryption...");
    await initializeEncryption(cryptoProvider);
    console.log("[datasetService] Encryption initialized successfully.");

    // Count total rows
    let totalRows = 0;
    console.log("[datasetService] Pre-scanning file to count total rows...");
    await new Promise((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        step: function() {
          totalRows++;
        },
        complete: function() {
          console.log(`[datasetService] Pre-scan complete. Total rows found: ${totalRows}`);
          resolve(null);
        },
        error: function(err) {
          console.error("[datasetService] Error during pre-scan:", err);
          reject(err);
        }
      });
    });

    if (totalRows === 0) {
      console.log("[datasetService] Total rows is 0. Completing prematurely.");
      callbacks.onStatusChange('success');
      callbacks.onProgress(100);
      callbacks.onComplete();
      return;
    }

    let chunkIndex = 0;
    let processedRowsCount = 0;
    let rowBuffer: any[] = [];
    let currentColumns: string[] = [];
    
    // Generate a unique identifier for this dataset
    const datasetId = crypto.randomUUID();

    const uploadBuffer = async () => {
      console.log(`[datasetService] uploadBuffer called. Elements in buffer: ${rowBuffer.length}, chunkIndex: ${chunkIndex}`);
      if (rowBuffer.length === 0) return;
      
      callbacks.onStatusChange('uploading');
      
      const payload = {
        dataset_id: datasetId,
        owner_address: address,
        lab_address: labAddress,
        filename: file.name,
        chunk_index: chunkIndex,
        columns: currentColumns,
        encrypted_rows: rowBuffer
      };

      console.log(`[datasetService] Sending payload to backend:`, { 
        dataset_id: payload.dataset_id,
        filename: payload.filename, 
        chunk_index: payload.chunk_index, 
        rows_count: payload.encrypted_rows.length 
      });

      try {
        await uploadDatasetChunk(payload);
        console.log(`[datasetService] Upload successful for chunkIndex ${chunkIndex}.`);
      } catch (err) {
        console.error(`[datasetService] Upload failed for chunkIndex ${chunkIndex}:`, err);
        throw err;
      }
      
      chunkIndex++;
      rowBuffer = []; // clear buffer
      
      if (processedRowsCount < totalRows) {
         callbacks.onStatusChange('encrypting');
      }
    };

    console.log("[datasetService] Starting actual file processing via Papa.parse...");
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      step: function(results, parser) {
        parser.pause();

        (async () => {
          try {
            if (!currentColumns.length && results.meta.fields) {
              currentColumns = results.meta.fields;
              console.log("[datasetService] Parsed columns:", currentColumns);
            }

            const row = results.data as any;
            if (row && Object.keys(row).length > 0) {
              console.log(`[datasetService] Encrypting row ${processedRowsCount + 1}/${totalRows}`);
              const encryptedRes = await encryptRow(row, currentColumns);
              rowBuffer.push(encryptedRes);
              processedRowsCount++;

              const progress = Math.min(99, Math.floor((processedRowsCount / totalRows) * 100));
              callbacks.onProgress(progress);

              console.log(`[datasetService] Row ${processedRowsCount} encrypted. Buffer size: ${rowBuffer.length}`);

              if (rowBuffer.length >= 5) {
                console.log("[datasetService] Buffer reached limit (5), triggering upload...");
                await uploadBuffer();
                console.log("[datasetService] Upload complete, resuming parser...");
              }
            }
          } catch (err: any) {
            console.error(`[datasetService] Error encrypting row ${processedRowsCount + 1}:`, err);
            parser.abort();
            callbacks.onError(err);
            return;
          }
          parser.resume();
        })();
      },
      complete: function() {
        console.log("[datasetService] Papa.parse complete callback hit. Processed rows:", processedRowsCount);
        (async () => {
          try {
            if (rowBuffer.length > 0) {
              console.log("[datasetService] Uploading remaining rows in buffer...", rowBuffer.length);
              await uploadBuffer();
            }
            console.log("[datasetService] Process entirely finished.");
            callbacks.onStatusChange('success');
            callbacks.onProgress(100);
            callbacks.onComplete();
          } catch (err: any) {
            console.error("[datasetService] Error in complete handler:", err);
            callbacks.onError(err);
          }
        })();
      },
      error: function(err: any) {
        console.error("[datasetService] PapaParse error:", err);
        callbacks.onError(new Error(err.message));
      }
    });

  } catch (err: any) {
    console.error("[datasetService] Top level error:", err);
    callbacks.onError(err);
  }
};

