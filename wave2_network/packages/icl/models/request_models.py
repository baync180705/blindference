from pydantic import BaseModel


class HealthRequest(BaseModel):
    message: str = "ok"
