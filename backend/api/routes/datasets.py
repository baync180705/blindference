from fastapi import APIRouter
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
