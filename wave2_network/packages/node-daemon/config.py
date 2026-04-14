from pydantic import BaseModel


class NodeDaemonConfig(BaseModel):
    icl_base_url: str = "http://localhost:8000"
