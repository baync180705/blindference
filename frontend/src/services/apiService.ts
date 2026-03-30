export const getAILabs = async () => {
    const res = await fetch("http://127.0.0.1:8000/api/users/labs");
    if (!res.ok) throw new Error("Failed to fetch AI Labs");
    return res.json();
}

export const uploadDatasetChunk = async (payload: any) => {
  console.log("[apiService] Stringifying payload...");
  let body;
  try {
    body = JSON.stringify(payload, (key, value) =>
      typeof value === 'bigint' ? value.toString() : value
    );
    console.log(`[apiService] Payload stringified. Size: ${body.length} bytes`);
  } catch (err) {
    console.error("[apiService] JSON stringify failed:", err);
    throw err;
  }

  console.log("[apiService] Executing fetch to 127.0.0.1:8000/api/datasets/upload_chunk...");
  const res = await fetch("http://127.0.0.1:8000/api/datasets/upload_chunk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
  });
  console.log(`[apiService] Fetch response status: ${res.status}`);
  if (!res.ok) throw new Error("Failed to upload chunk");
  return res.json();
};

export const getLabDatasets = async (labAddress: string) => {
  const res = await fetch(`http://127.0.0.1:8000/api/datasets/lab/${labAddress}`);
  if (!res.ok) throw new Error("Failed to fetch lab datasets");
  return res.json();
};

export const getDatasetPayload = async (datasetId: string) => {
  const res = await fetch(`http://127.0.0.1:8000/api/datasets/${datasetId}`);
  if (!res.ok) throw new Error("Failed to fetch dataset payload");
  return res.json();
};

