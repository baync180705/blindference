import logging
import motor.motor_asyncio
from core.config import MONGO_URI

logger = logging.getLogger("blindinference")

class AppState:
    db: motor.motor_asyncio.AsyncIOMotorDatabase = None

state = AppState()

def connect_to_mongo():
    logger.info("Connected to MongoDB Atlas")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    state.db = client.get_database("blindinference")
    return client

def close_mongo_connection(client):
    logger.info("Shutting down MongoDB connection")
    client.close()
