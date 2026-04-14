from pydantic import BaseModel


class MongoRecord(BaseModel):
    id: str = "stub"
