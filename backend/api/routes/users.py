from fastapi import APIRouter
from core.database import state

router = APIRouter()

@router.get("/labs")
async def get_ai_labs():
    cursor = state.db.users.find({"role": "ai_lab"})
    labs = await cursor.to_list(length=100)
    return [{"address": lab["address"], "created_at": lab.get("created_at")} for lab in labs]
