from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from models.dataset import UploadChunkRequest
from core.database import state

router = APIRouter()

@router.post("/upload_chunk")
async def upload_dataset_chunk(req: UploadChunkRequest):
    update_data = {
        "$setOnInsert": {
            "dataset_id": req.dataset_id,
            "owner_address": req.owner_address.lower(),
            "lab_address": req.lab_address.lower(),
            "filename": req.filename,
            "columns": req.columns,
            "created_at": datetime.now(timezone.utc)
        },
        "$push": {
            "encrypted_rows": { "$each": req.encrypted_rows }
        }
    }
    
    await state.db.datasets.update_one(
        {"dataset_id": req.dataset_id},
        update_data,
        upsert=True
    )
    return {"status": "success", "chunk_index": req.chunk_index}

@router.get("/lab/{lab_address}")
async def get_lab_datasets(lab_address: str):
    cursor = state.db.datasets.find(
        {"lab_address": lab_address.lower()},
        {"encrypted_rows": 0} # Exclude the massive array
    )
    datasets = await cursor.to_list(length=100)
    for ds in datasets:
        ds["_id"] = str(ds["_id"])
    return datasets

@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    dataset = await state.db.datasets.find_one({"dataset_id": dataset_id})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    dataset["_id"] = str(dataset["_id"])
    return dataset
