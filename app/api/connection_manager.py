import asyncio
import logging
from typing import Dict, List, Set

from fastapi import WebSocket

from app.db.mysql import get_license_plates_by_company
import json
import time

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[Dict]] = {
            "topic-gps-218": [],
            "topic-load-218": [],
            "topic-sensor-218": [],
            "alerts": [],
            "test_topic": [],
        }
        self.license_plate_cache = {}
        self.CACHE_TTL = 300

    async def connect(self, websocket: WebSocket, topics: List[str], cid: int, pn: str = None):
        await websocket.accept()
        connection_data = {"websocket": websocket, "cid": cid, "pn": pn}
        for topic in topics:
            if topic in self.active_connections:
                self.active_connections[topic].append(connection_data)
        logging.info(f"✅ New client connected and subscribed to {topics} with cid={cid} and pn={pn}")

    def disconnect(self, websocket: WebSocket):
        disconnected = False
        for topic in self.active_connections:
            initial_len = len(self.active_connections[topic])
            self.active_connections[topic] = [
                conn for conn in self.active_connections[topic] if conn["websocket"] != websocket
            ]
            if len(self.active_connections[topic]) < initial_len:
                disconnected = True

        if disconnected:
            logging.debug(f"🔌 Client disconnected")

    async def broadcast(self, topic: str, message: str):
        if topic in self.active_connections:
            data = json.loads(message)
            plate = data.get("licensePlateNumber")

            for connection_data in self.active_connections[topic]:
                cid = connection_data["cid"]
                pn = connection_data["pn"]

                if cid != 2:
                    if cid not in self.license_plate_cache or (time.time() - self.license_plate_cache[cid]["timestamp"]) > self.CACHE_TTL:
                        self.license_plate_cache[cid] = {
                            "plates": set(get_license_plates_by_company(cid)),
                            "timestamp": time.time()
                        }

                    allowed_plates = self.license_plate_cache[cid]["plates"]
                    if plate not in allowed_plates:
                        logging.debug(f"🚫 Plate {plate} not allowed for cid {cid}")
                        continue

                if pn and plate != pn:
                    logging.debug(f"🚫 Plate {plate} does not match pn {pn}")
                    continue

                websocket = connection_data["websocket"]
                logging.info(f"📤 Sending message to cid={cid}, pn={pn}")
                await websocket.send_text(message)

manager = ConnectionManager()
