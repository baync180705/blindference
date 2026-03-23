from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blindinference")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BlindInference API")
    # ...init resources (db connections, clients, etc.)...
    yield
    # ...cleanup resources...
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

