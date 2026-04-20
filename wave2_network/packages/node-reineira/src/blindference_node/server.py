from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from blindference_node.worker import BlindferenceDemoWorker


class TaskEnvelope(BaseModel):
    role: str
    request: dict


def create_node_app(worker: BlindferenceDemoWorker) -> FastAPI:
    app = FastAPI(title="Blindference Node Runtime", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/internal/task")
    async def enqueue_task(payload: TaskEnvelope) -> dict[str, str]:
        if payload.role not in {"leader", "verifier"}:
            raise HTTPException(status_code=400, detail="invalid node role")
        await worker.enqueue_task(payload.request, payload.role)
        return {
            "status": "accepted",
            "request_id": str(payload.request.get("request_id", "")),
            "task_id": str(payload.request.get("task_id", "")),
            "role": payload.role,
        }

    return app
