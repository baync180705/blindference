import json
import logging
import os
import inspect
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from pathlib import Path

import jwt
import motor.motor_asyncio
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_defunct

load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

CHUNK_SIZE = 1024 * 1024
ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
AUTH_NONCE_TTL_MINUTES = 5
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
PPML_EXPORT_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "ppml" / "model_export.json",
    Path(__file__).resolve().parents[2] / "PPML" / "model_export.json",
)
JWT_SECRET = os.getenv("JWT_SECRET", "blindference-dev-secret")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blindinference")


class AuthNonceRequest(BaseModel):
    address: str
    role: str


class AuthVerifyRequest(BaseModel):
    address: str
    role: str
    nonce_id: str
    signature: str


class UserProfilePayload(BaseModel):
    display_name: str | None = None
    organization: str | None = None
    bio: str | None = None
    profile_uri: str | None = None


class DatasetManifestPayload(BaseModel):
    file_id: str
    filename: str
    lab_address: str
    model_id: str | None = None
    content_type: str | None = None
    notes: str | None = None


class SubmissionPayload(BaseModel):
    request_id: str
    model_id: str
    lab_address: str
    tx_hash: str | None = None
    status: str
    result_handle: str | None = None
    plaintext_result: str | None = None


def normalize_address(address: str) -> str:
    if not ADDRESS_PATTERN.match(address):
        raise HTTPException(status_code=400, detail="invalid wallet address")
    return address.lower()


def validate_role(role: str) -> str:
    if role not in {"data_source", "ai_lab"}:
        raise HTTPException(status_code=400, detail="invalid role")
    return role


def build_auth_message(address: str, role: str, nonce: str, issued_at: datetime) -> str:
    issued_at_iso = issued_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        "Blindference Authentication\n"
        f"Wallet: {address}\n"
        f"Role: {role}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at_iso}\n"
        "Sign this message to authenticate with Blindference."
    )


def create_access_token(address: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": address,
        "role": role,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(authorization: str | None) -> dict:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    if token == "":
        raise HTTPException(status_code=401, detail="missing bearer token")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as error:
        raise HTTPException(status_code=401, detail="invalid bearer token") from error

    return payload


def require_subject_match(authorization: str | None, address: str) -> dict:
    payload = decode_access_token(authorization)
    if payload.get("sub") != address:
        raise HTTPException(status_code=403, detail="token subject does not match wallet address")
    return payload


def require_role(payload: dict, role: str) -> None:
    if payload.get("role") != role:
        raise HTTPException(status_code=403, detail=f"{role} role required")


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


async def maybe_await(result):
    if inspect.isawaitable(result):
        await result


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


@app.post("/api/v1/auth/nonce", tags=["auth"])
async def create_auth_nonce(request: AuthNonceRequest):
    address = normalize_address(request.address)
    role = validate_role(request.role)
    issued_at = datetime.now(timezone.utc)
    nonce = secrets.token_urlsafe(24)
    message = build_auth_message(address, role, nonce, issued_at)

    auth_record = {
        "address": address,
        "role": role,
        "nonce": nonce,
        "issued_at": issued_at,
        "expires_at": issued_at + timedelta(minutes=AUTH_NONCE_TTL_MINUTES),
        "used": False,
    }

    result = await app.state.db.auth_nonces.insert_one(auth_record)

    return {
        "nonce_id": str(result.inserted_id),
        "message": message,
        "expires_in_seconds": AUTH_NONCE_TTL_MINUTES * 60,
    }


@app.post("/api/v1/auth/verify", tags=["auth"])
async def verify_auth_signature(request: AuthVerifyRequest):
    address = normalize_address(request.address)
    role = validate_role(request.role)

    try:
        nonce_object_id = ObjectId(request.nonce_id)
    except Exception as error:
        raise HTTPException(status_code=400, detail="invalid nonce_id") from error

    nonce_record = await app.state.db.auth_nonces.find_one({"_id": nonce_object_id})
    if nonce_record is None:
        raise HTTPException(status_code=404, detail="auth nonce not found")

    if nonce_record.get("used"):
        raise HTTPException(status_code=409, detail="auth nonce already used")

    now = datetime.now(timezone.utc)
    expires_at = nonce_record["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise HTTPException(status_code=410, detail="auth nonce expired")

    if nonce_record["address"] != address:
        raise HTTPException(status_code=400, detail="nonce address mismatch")
    if nonce_record["role"] != role:
        raise HTTPException(status_code=400, detail="nonce role mismatch")

    message = build_auth_message(
        nonce_record["address"],
        nonce_record["role"],
        nonce_record["nonce"],
        nonce_record["issued_at"].replace(tzinfo=timezone.utc)
        if nonce_record["issued_at"].tzinfo is None
        else nonce_record["issued_at"],
    )

    try:
        recovered_address = Account.recover_message(
            encode_defunct(text=message),
            signature=request.signature,
        ).lower()
    except Exception as error:
        raise HTTPException(status_code=400, detail="invalid signature payload") from error

    if recovered_address != address:
        raise HTTPException(status_code=401, detail="signature does not match wallet address")

    await app.state.db.auth_nonces.update_one(
        {"_id": nonce_object_id},
        {"$set": {"used": True, "verified_at": now}},
    )

    await app.state.db.users.update_one(
        {"address": address},
        {
            "$set": {
                "address": address,
                "role": role,
                "last_authenticated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    token = create_access_token(address, role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
    }


@app.get("/api/v1/profile/{address}", tags=["profile"])
async def get_user_profile(address: str, authorization: str | None = Header(default=None)):
    normalized_address = normalize_address(address)
    token_payload = require_subject_match(authorization, normalized_address)

    user = await app.state.db.users.find_one({"address": normalized_address})
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    profile = await app.state.db.user_profiles.find_one({"address": normalized_address}) or {}
    return {
        "address": normalized_address,
        "role": user.get("role", token_payload.get("role")),
        "display_name": profile.get("display_name"),
        "organization": profile.get("organization"),
        "bio": profile.get("bio"),
        "profile_uri": profile.get("profile_uri"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }


@app.put("/api/v1/profile/{address}", tags=["profile"])
async def update_user_profile(
    address: str,
    payload: UserProfilePayload,
    authorization: str | None = Header(default=None),
):
    normalized_address = normalize_address(address)
    token_payload = require_subject_match(authorization, normalized_address)
    now = datetime.now(timezone.utc)

    sanitized_profile = {
        "display_name": payload.display_name.strip() if payload.display_name else None,
        "organization": payload.organization.strip() if payload.organization else None,
        "bio": payload.bio.strip() if payload.bio else None,
        "profile_uri": payload.profile_uri.strip() if payload.profile_uri else None,
    }

    await app.state.db.users.update_one(
        {"address": normalized_address},
        {
            "$set": {
                "address": normalized_address,
                "role": token_payload.get("role"),
                "last_authenticated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    await app.state.db.user_profiles.update_one(
        {"address": normalized_address},
        {
            "$set": {
                **sanitized_profile,
                "updated_at": now,
            },
            "$setOnInsert": {
                "address": normalized_address,
                "created_at": now,
            },
        },
        upsert=True,
    )

    return {
        "address": normalized_address,
        "role": token_payload.get("role"),
        **sanitized_profile,
        "updated_at": now,
    }


@app.post("/api/v1/datasets/manifest", tags=["datasets"])
async def create_dataset_manifest(
    payload: DatasetManifestPayload,
    authorization: str | None = Header(default=None),
):
    token_payload = decode_access_token(authorization)
    require_role(token_payload, "data_source")
    owner_address = normalize_address(token_payload["sub"])
    lab_address = normalize_address(payload.lab_address)
    now = datetime.now(timezone.utc)

    manifest = {
        "file_id": payload.file_id,
        "filename": payload.filename.strip(),
        "owner_address": owner_address,
        "lab_address": lab_address,
        "model_id": payload.model_id.strip() if payload.model_id else None,
        "content_type": payload.content_type.strip() if payload.content_type else None,
        "notes": payload.notes.strip() if payload.notes else None,
        "status": "uploaded",
        "created_at": now,
        "updated_at": now,
    }

    result = await app.state.db.dataset_manifests.insert_one(manifest)
    return {
        "dataset_id": str(result.inserted_id),
        **manifest,
    }


@app.get("/api/v1/datasets/outgoing/{address}", tags=["datasets"])
async def list_outgoing_datasets(address: str, authorization: str | None = Header(default=None)):
    normalized_address = normalize_address(address)
    token_payload = require_subject_match(authorization, normalized_address)
    require_role(token_payload, "data_source")

    cursor = app.state.db.dataset_manifests.find(
        {"owner_address": normalized_address},
    ).sort("created_at", -1)
    manifests = await cursor.to_list(length=100)
    for manifest in manifests:
        manifest["dataset_id"] = str(manifest.pop("_id"))
    return manifests


@app.get("/api/v1/datasets/incoming/{address}", tags=["datasets"])
async def list_incoming_datasets(address: str, authorization: str | None = Header(default=None)):
    normalized_address = normalize_address(address)
    token_payload = require_subject_match(authorization, normalized_address)
    require_role(token_payload, "ai_lab")

    cursor = app.state.db.dataset_manifests.find(
        {"lab_address": normalized_address},
    ).sort("created_at", -1)
    manifests = await cursor.to_list(length=100)
    for manifest in manifests:
        manifest["dataset_id"] = str(manifest.pop("_id"))
    return manifests


@app.post("/api/v1/submissions", tags=["submissions"])
async def upsert_submission(
    payload: SubmissionPayload,
    authorization: str | None = Header(default=None),
):
    token_payload = decode_access_token(authorization)
    require_role(token_payload, "data_source")
    owner_address = normalize_address(token_payload["sub"])
    lab_address = normalize_address(payload.lab_address)
    now = datetime.now(timezone.utc)

    update = {
        "$set": {
            "owner_address": owner_address,
            "lab_address": lab_address,
            "model_id": payload.model_id.strip(),
            "tx_hash": payload.tx_hash.strip() if payload.tx_hash else None,
            "status": payload.status.strip(),
            "result_handle": payload.result_handle.strip() if payload.result_handle else None,
            "plaintext_result": payload.plaintext_result.strip() if payload.plaintext_result else None,
            "updated_at": now,
        },
        "$setOnInsert": {
            "request_id": payload.request_id.strip(),
            "created_at": now,
        },
    }

    await app.state.db.inference_submissions.update_one(
        {"request_id": payload.request_id.strip(), "owner_address": owner_address},
        update,
        upsert=True,
    )

    document = await app.state.db.inference_submissions.find_one(
        {"request_id": payload.request_id.strip(), "owner_address": owner_address}
    )
    if document is None:
        raise HTTPException(status_code=500, detail="failed to persist submission metadata")

    document["submission_id"] = str(document.pop("_id"))
    return document


@app.get("/api/v1/submissions/outgoing/{address}", tags=["submissions"])
async def list_outgoing_submissions(address: str, authorization: str | None = Header(default=None)):
    normalized_address = normalize_address(address)
    token_payload = require_subject_match(authorization, normalized_address)
    require_role(token_payload, "data_source")

    cursor = app.state.db.inference_submissions.find(
        {"owner_address": normalized_address},
    ).sort("created_at", -1)
    submissions = await cursor.to_list(length=100)
    for submission in submissions:
        submission["submission_id"] = str(submission.pop("_id"))
    return submissions


@app.get("/api/v1/submissions/incoming/{address}", tags=["submissions"])
async def list_incoming_submissions(address: str, authorization: str | None = Header(default=None)):
    normalized_address = normalize_address(address)
    token_payload = require_subject_match(authorization, normalized_address)
    require_role(token_payload, "ai_lab")

    cursor = app.state.db.inference_submissions.find(
        {"lab_address": normalized_address},
    ).sort("created_at", -1)
    submissions = await cursor.to_list(length=100)
    for submission in submissions:
        submission["submission_id"] = str(submission.pop("_id"))
    return submissions


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
        await maybe_await(upload_stream.abort())
        raise HTTPException(status_code=500, detail=f"failed to stream dataset into GridFS: {error}") from error
    finally:
        await file.close()

    await maybe_await(upload_stream.close())
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
            await maybe_await(download_stream.close())

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
