import asyncio
import json
import logging
from fastapi import WebSocket, FastAPI, WebSocketDisconnect
from app.api.connection_manager import manager
from app.db.mysql import get_license_plates_by_company
import uuid
from app.db.mongo import mongo_db

def register_websockets(app: FastAPI):
    @app.websocket("/ws/gps")
    async def gps_ws(websocket: WebSocket, cid: int, pn: str = None):
        await manager.connect(websocket, ["topic-gps-218"], cid, pn)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logging.debug(f"Client disconnected from /ws/gps")

    @app.websocket("/ws/load")
    async def load_ws(websocket: WebSocket, cid: int, pn: str = None):
        await manager.connect(websocket, ["topic-load-218"], cid, pn)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logging.debug(f"Client disconnected from /ws/load")

    @app.websocket("/ws/sensor")
    async def sensor_ws(websocket: WebSocket, cid: int, pn: str = None):
        await manager.connect(websocket, ["topic-sensor-218"], cid, pn)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logging.debug(f"Client disconnected from /ws/sensor")

    @app.websocket("/ws/alerts")
    async def alerts_ws(websocket: WebSocket, cid: int, pn: str = None):
        await manager.connect(websocket, ["alerts"], cid, pn)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logging.debug(f"Client disconnected from /ws/alerts")
