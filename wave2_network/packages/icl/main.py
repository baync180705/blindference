from fastapi import FastAPI

from routers.admin import router as admin_router
from routers.coverage import router as coverage_router
from routers.disputes import router as disputes_router
from routers.inference import router as inference_router
from routers.models import router as models_router
from routers.nodes import router as nodes_router
from routers.operators import router as operators_router

app = FastAPI(title="Blindference ICL", version="0.1.0")

app.include_router(inference_router)
app.include_router(nodes_router)
app.include_router(models_router)
app.include_router(coverage_router)
app.include_router(disputes_router)
app.include_router(admin_router)
app.include_router(operators_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
