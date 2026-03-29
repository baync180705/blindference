from pydantic import BaseModel
from typing import List, Any

class UploadChunkRequest(BaseModel):
    dataset_id: str
    owner_address: str
    lab_address: str
    filename: str
    chunk_index: int
    columns: List[str]
    encrypted_rows: List[List[Any]]
