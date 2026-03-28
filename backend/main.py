import os
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import motor.motor_asyncio
import jwt

from dotenv import load_dotenv
load_dotenv()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blindinference")

# Env vars
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://buildathon:buildathon123@cluster0.mongodb.net/?retryWrites=true&w=majority") # Fallback dummy URI if not provided
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-blindference")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24 * 7 # 1 week

class AppState:
    db: motor.motor_asyncio.AsyncIOMotorDatabase = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BlindInference API")
    # Init MongoDB
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    state.db = client.get_database("blindinference")
    logger.info("Connected to MongoDB Atlas")
    yield
    client.close()
    logger.info("Shutting down BlindInference API")

app = FastAPI(
    title="BlindInference API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    if request.url.path != "/health":
        logger.info(
            f"{request.method} {request.url.path} "
            f"completed_in={process_time:.2f}ms status={response.status_code}"
        )
    return response

# Pydantic Models for Auth
class LoginRequest(BaseModel):
    address: str

class RegisterRequest(BaseModel):
    address: str
    role: str # "client" or "ai_lab"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

@app.post("/api/auth/login", tags=["auth"])
async def login(req: LoginRequest):
    user = await state.db.users.find_one({"address": req.address.lower()})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found (Registration required)")
    
    token = create_access_token({"sub": user["address"], "role": user.get("role")})
    return {"access_token": token, "token_type": "bearer", "role": user.get("role")}

@app.post("/api/auth/register", tags=["auth"])
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

from typing import List, Any

class UploadChunkRequest(BaseModel):
    owner_address: str
    lab_address: str
    filename: str
    chunk_index: int
    columns: List[str]
    encrypted_rows: List[List[Any]]

@app.get("/api/users/labs", tags=["users"])
async def get_ai_labs():
    cursor = state.db.users.find({"role": "ai_lab"})
    labs = await cursor.to_list(length=100)
    return [{"address": lab["address"], "created_at": lab.get("created_at")} for lab in labs]

@app.post("/api/datasets/upload_chunk", tags=["datasets"])
async def upload_dataset_chunk(req: UploadChunkRequest):
    chunk_doc = {
        "owner_address": req.owner_address.lower(),
        "lab_address": req.lab_address.lower(),
        "filename": req.filename,
        "chunk_index": req.chunk_index,
        "columns": req.columns,
        "encrypted_rows": req.encrypted_rows,
        "created_at": datetime.now(timezone.utc)
    }
    await state.db.dataset_chunks.insert_one(chunk_doc)
    return {"status": "success", "chunk_index": req.chunk_index}

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}

@app.get("/", tags=["system"])
async def root():
    return {"message": "BlindInference backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST"), port=int(os.getenv("PORT")), reload=True)