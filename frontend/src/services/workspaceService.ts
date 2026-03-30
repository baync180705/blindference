const BACKEND_BASE_URL = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? 'http://127.0.0.1:8000';

export type DatasetManifest = {
  dataset_id: string;
  file_id: string;
  filename: string;
  owner_address: string;
  lab_address: string;
  model_id?: string | null;
  content_type?: string | null;
  notes?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type SubmissionRecord = {
  submission_id: string;
  request_id: string;
  owner_address: string;
  lab_address: string;
  model_id: string;
  tx_hash?: string | null;
  status: string;
  result_handle?: string | null;
  plaintext_result?: string | null;
  created_at: string;
  updated_at: string;
};

function authHeaders(jwt: string, includeJson = true) {
  return {
    ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
    Authorization: `Bearer ${jwt}`,
  };
}

export async function uploadEncryptedDataset(file: File): Promise<{ file_id: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/dataset/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to upload encrypted dataset');
  }

  return response.json() as Promise<{ file_id: string }>;
}

export async function createDatasetManifest(
  jwt: string,
  payload: {
    file_id: string;
    filename: string;
    lab_address: string;
    model_id?: string;
    content_type?: string;
    notes?: string;
  },
): Promise<DatasetManifest> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/datasets/manifest`, {
    method: 'POST',
    headers: authHeaders(jwt),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to create dataset manifest');
  }

  return response.json() as Promise<DatasetManifest>;
}

export async function getOutgoingDatasets(address: string, jwt: string): Promise<DatasetManifest[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/datasets/outgoing/${address}`, {
    method: 'GET',
    headers: authHeaders(jwt, false),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to fetch outgoing datasets');
  }

  return response.json() as Promise<DatasetManifest[]>;
}

export async function getIncomingDatasets(address: string, jwt: string): Promise<DatasetManifest[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/datasets/incoming/${address}`, {
    method: 'GET',
    headers: authHeaders(jwt, false),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to fetch incoming datasets');
  }

  return response.json() as Promise<DatasetManifest[]>;
}

export async function upsertSubmission(
  jwt: string,
  payload: {
    request_id: string;
    model_id: string;
    lab_address: string;
    tx_hash?: string;
    status: string;
    result_handle?: string;
    plaintext_result?: string;
  },
): Promise<SubmissionRecord> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/submissions`, {
    method: 'POST',
    headers: authHeaders(jwt),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to persist submission metadata');
  }

  return response.json() as Promise<SubmissionRecord>;
}

export async function getOutgoingSubmissions(address: string, jwt: string): Promise<SubmissionRecord[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/submissions/outgoing/${address}`, {
    method: 'GET',
    headers: authHeaders(jwt, false),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to fetch outgoing submissions');
  }

  return response.json() as Promise<SubmissionRecord[]>;
}

export async function getIncomingSubmissions(address: string, jwt: string): Promise<SubmissionRecord[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/submissions/incoming/${address}`, {
    method: 'GET',
    headers: authHeaders(jwt, false),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to fetch incoming submissions');
  }

  return response.json() as Promise<SubmissionRecord[]>;
}
