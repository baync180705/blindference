import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.database import connect_to_mongo, close_mongo_connection
from api.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blindinference")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BlindInference API")
    client = connect_to_mongo()
    yield
    close_mongo_connection(client)

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
    if request.url.path != "/health" and request.url.path != "/":
        logger.info(
            f"{request.method} {request.url.path} "
            f"completed_in={process_time:.2f}ms status={response.status_code}"
        )
    return response

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)