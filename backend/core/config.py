import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://buildathon:buildathon123@cluster0.mongodb.net/?retryWrites=true&w=majority")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-blindference")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24 * 7
