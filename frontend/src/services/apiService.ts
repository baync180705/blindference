export const getAILabs = async () => {
    const res = await fetch("http://localhost:8000/api/users/labs");
    if (!res.ok) throw new Error("Failed to fetch AI Labs");
    return res.json();
}

export const uploadDatasetChunk = async (payload: any) => {
  const res = await fetch("http://localhost:8000/api/datasets/upload_chunk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to upload chunk");
  return res.json();
};
