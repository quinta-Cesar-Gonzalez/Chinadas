from pymongo import MongoClient, ASCENDING, DESCENDING
from app.core.config import MONGO_URI
import logging

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["Quinta"]

def close_mongo_connection():
    mongo_client.close()

def create_indexes():
    try:
        mongo_db.TruckRideLog.create_index([
            ("licensePlateNumber", ASCENDING),
            ("receiveTime", DESCENDING)
        ])
        mongo_db.Sensors.create_index([
            ("vehicleId", ASCENDING),
            ("receiveTime", DESCENDING),
            ("licensePlateNumber", ASCENDING),
            ("realPosition", ASCENDING)
        ])
        mongo_db.Loads.create_index([
            ("vehicleId", ASCENDING),
            ("licensePlateNumber", ASCENDING),
            ("realPosition", ASCENDING),
            ("receiveTime", DESCENDING)
        ])
        logging.info("✅ Índices de MongoDB creados correctamente.")
    except Exception as e:
        logging.error(f"❌ Error creando índices de MongoDB: {e}")
