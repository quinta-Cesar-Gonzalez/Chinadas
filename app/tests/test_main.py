import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 404

def test_websocket_gps():
    with client.websocket_connect("/ws/gps?cid=1") as websocket:
        websocket.close()

def test_websocket_load():
    with client.websocket_connect("/ws/load?cid=1") as websocket:
        websocket.close()

def test_websocket_sensor():
    with client.websocket_connect("/ws/sensor?cid=1") as websocket:
        websocket.close()

def test_websocket_alerts():
    with client.websocket_connect("/ws/alerts?cid=1") as websocket:
        websocket.close()

import os

def test_logging():
    assert os.path.exists("logs/info.log")
    assert os.path.exists("logs/warning.log")
    assert os.path.exists("logs/error.log")

