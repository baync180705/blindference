import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import motor.motor_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from bson import ObjectId

load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

CHUNK_SIZE = 1024 * 1024
PPML_EXPORT_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "ppml" / "model_export.json",
    Path(__file__).resolve().parents[2] / "PPML" / "model_export.json",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blindinference")


def get_model_export_path() -> Path | None:
    for candidate in PPML_EXPORT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def get_gridfs_bucket(request: Request) -> AsyncIOMotorGridFSBucket:
    bucket = getattr(request.app.state, "fs", None)
    if bucket is None:
        raise HTTPException(status_code=503, detail="GridFS storage is not initialized")
    return bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BlindInference API")
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI must be set before starting the backend")

    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    database = mongo_client["blindference_db"]
    gridfs_bucket = AsyncIOMotorGridFSBucket(database)

    app.state.mongo_client = mongo_client
    app.state.db = database
    app.state.fs = gridfs_bucket

    try:
        yield
    finally:
        mongo_client.close()
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

# Basic request/response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed_in={process_time:.2f}ms status={response.status_code}"
    )
    return response

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}

# Example root endpoint
@app.get("/", tags=["system"])
async def root():
    return {"message": "BlindInference backend is running"}


@app.post("/api/v1/dataset/upload", tags=["dataset"])
async def upload_dataset(request: Request, file: UploadFile = File(...)):
    fs = get_gridfs_bucket(request)

    upload_stream = fs.open_upload_stream(
        file.filename or "encrypted_dataset.bin",
        chunk_size_bytes=CHUNK_SIZE,
        metadata={
            "content_type": file.content_type or "application/octet-stream",
        },
    )

    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            await upload_stream.write(chunk)
    except Exception as error:
        await upload_stream.abort()
        raise HTTPException(status_code=500, detail=f"failed to stream dataset into GridFS: {error}") from error
    finally:
        await file.close()

    await upload_stream.close()
    return {"file_id": str(upload_stream._id)}


@app.get("/api/v1/dataset/download/{file_id}", tags=["dataset"])
async def download_dataset(file_id: str, request: Request):
    fs = get_gridfs_bucket(request)

    try:
        object_id = ObjectId(file_id)
    except Exception as error:
        raise HTTPException(status_code=400, detail="invalid GridFS file_id") from error

    try:
        download_stream = await fs.open_download_stream(object_id)
    except NoFile as error:
        raise HTTPException(status_code=404, detail="dataset not found") from error

    async def iter_chunks():
        try:
            while True:
                chunk = await download_stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        finally:
            await download_stream.close()

    return StreamingResponse(
        iter_chunks(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file_id}.bin"'},
    )


@app.get("/api/v1/model/status", tags=["model"])
async def model_status():
    model_export_path = get_model_export_path()
    if model_export_path is None:
        return {"status": "processing"}

    with model_export_path.open("r", encoding="utf-8") as export_file:
        return json.load(export_file)
