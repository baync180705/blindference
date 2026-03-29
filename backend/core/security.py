from datetime import datetime, timedelta, timezone
import jwt
from core.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt
