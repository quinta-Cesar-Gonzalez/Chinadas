import json
import logging
from fastapi import APIRouter, HTTPException, Body
from app.api.kafka_consumer import handle_gps_message, handle_sensor_message, handle_load_message

router = APIRouter()

# Defining a model for the incoming request body for better validation and documentation
from pydantic import BaseModel
class BridgeMessage(BaseModel):
    message: str

def get_message_type(parsed_message: dict) -> str:
    """
    Inspects the parsed message to determine its type (gps, sensor, or load).
    This is a simple heuristic based on expected unique keys.
    """
    if "latitude" in parsed_message and "longitude" in parsed_message:
        return "gps"
    if "pressure" in parsed_message and "temperature" in parsed_message:
        return "sensor"
    if "nowThreadDepth" in parsed_message:
        return "load"
    return "unknown"

@router.post("/api/messages")
async def receive_message(payload: BridgeMessage):
    """
    Receives a message from the Java bridge, determines its type,
    and forwards it to the appropriate handler.
    """
    try:
        logging.info(f"Received message from Java bridge: {payload.message}")

        # The message from Java is a JSON string, so we parse it
        parsed_data = json.loads(payload.message)

        message_type = get_message_type(parsed_data)

        logging.info(f"Determined message type: {message_type}")

        if message_type == "gps":
            await handle_gps_message(parsed_data)
        elif message_type == "sensor":
            await handle_sensor_message(parsed_data)
        elif message_type == "load":
            await handle_load_message(parsed_data)
        else:
            logging.warning(f"Unknown message type for payload: {payload.message}")
            raise HTTPException(status_code=400, detail="Unknown message type")

        return {"status": "success", "message_type": message_type}
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from message: {payload.message}")
        raise HTTPException(status_code=400, detail="Invalid JSON format in message payload")
    except Exception as e:
        logging.error(f"Error processing message from bridge: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
