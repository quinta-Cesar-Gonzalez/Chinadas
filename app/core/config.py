import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_URI = os.getenv("MYSQL_URI")

MONGO_URI = os.getenv("MONGO_URI")

    # KAFKA_CONFIG = {
    #     "bootstrap.servers": os.getenv("KAFKA_SERVERS"),
    #     "security.protocol": os.getenv("KAFKA_SECURITY"),
    #     "sasl.mechanism": os.getenv("KAFKA_MECHANISM"),
    #     "sasl.username": os.getenv("KAFKA_USERNAME"),
    #     "sasl.password": os.getenv("KAFKA_PASSWORD"),
    #     "auto.offset.reset": "latest",
    #     "group.id": os.getenv("KAFKA_GROUP_ID"),
    #     "enable.auto.commit": False,
    # }

KAFKA_CONFIG = {
    "bootstrap.servers": os.getenv("KAFKA_SERVERS"),
    "security.protocol": os.getenv("KAFKA_SECURITY"),
    "sasl.mechanism": os.getenv("KAFKA_MECHANISM"),
    "sasl.username": os.getenv("KAFKA_USERNAME"),
    "sasl.password": os.getenv("KAFKA_PASSWORD"),
    "group.id": os.getenv("KAFKA_GROUP_ID"),
    "auto.offset.reset": os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest"),
    "enable.auto.commit": os.getenv("KAFKA_ENABLE_AUTO_COMMIT", "true").lower() == "true",
    "auto.commit.interval.ms": int(os.getenv("KAFKA_AUTO_COMMIT_INTERVAL_MS", "1000")),
    "session.timeout.ms": int(os.getenv("KAFKA_SESSION_TIMEOUT_MS", "120000")),
    "request.timeout.ms": int(os.getenv("KAFKA_REQUEST_TIMEOUT_MS", "180000")),
}

SMARTTYRE_CONFIG = {
    "base_url": os.getenv("SMARTTYRE_BASE_URL"),
    "client_id": os.getenv("SMARTTYRE_CLIENT_ID"),
    "client_secret": os.getenv("SMARTTYRE_CLIENT_SECRET"),
    "sign_key": os.getenv("SMARTTYRE_SIGN_KEY"),
}
