from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from models.auth import LoginRequest, RegisterRequest
from core.security import create_access_token
from core.database import state

router = APIRouter()

@router.post("/login")
async def login(req: LoginRequest):
    user = await state.db.users.find_one({"address": req.address.lower()})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found (Registration required)")
    
    token = create_access_token({"sub": user["address"], "role": user.get("role")})
    return {"access_token": token, "token_type": "bearer", "role": user.get("role")}

@router.post("/register")
async def register(req: RegisterRequest):
    address = req.address.lower()
    
    if req.role not in ["client", "ai_lab"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'client' or 'ai_lab'")
        
    existing_user = await state.db.users.find_one({"address": address})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered")
        
    new_user = {
        "address": address,
        "role": req.role,
        "created_at": datetime.now(timezone.utc)
    }
    
    await state.db.users.insert_one(new_user)
    token = create_access_token({"sub": address, "role": req.role})
    
    return {"access_token": token, "token_type": "bearer", "role": req.role}
