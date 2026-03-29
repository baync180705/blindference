from pydantic import BaseModel

class LoginRequest(BaseModel):
    address: str

class RegisterRequest(BaseModel):
    address: str
    role: str # "client" or "ai_lab"
