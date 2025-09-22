import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.connection_manager import ConnectionManager

@pytest.fixture
def manager():
    return ConnectionManager()

@pytest.mark.asyncio
async def test_connect_disconnect(manager: ConnectionManager):
    websocket = AsyncMock()
    await manager.connect(websocket, ["test_topic"], 1)
    assert len(manager.active_connections["test_topic"]) == 1
    manager.disconnect(websocket)
    assert len(manager.active_connections["test_topic"]) == 0

@pytest.mark.asyncio
@patch("app.api.connection_manager.get_license_plates_by_company")
async def test_broadcast_with_filtering(mock_get_plates, manager: ConnectionManager):
    mock_get_plates.return_value = ["PLATE-1"]

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await manager.connect(websocket1, ["test_topic"], 1, "PLATE-1")
    await manager.connect(websocket2, ["test_topic"], 1, "PLATE-2")

    message = '{"licensePlateNumber": "PLATE-1"}'
    await manager.broadcast("test_topic", message)

    websocket1.send_text.assert_called_once_with(message)
    websocket2.send_text.assert_not_called()

@pytest.mark.asyncio
@patch("app.api.connection_manager.get_license_plates_by_company")
async def test_broadcast_without_filtering(mock_get_plates, manager: ConnectionManager):
    mock_get_plates.return_value = ["PLATE-1", "PLATE-2"]

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await manager.connect(websocket1, ["test_topic"], 2)
    await manager.connect(websocket2, ["test_topic"], 2)

    message = '{"licensePlateNumber": "PLATE-1"}'
    await manager.broadcast("test_topic", message)

    websocket1.send_text.assert_called_once_with(message)
    websocket2.send_text.assert_called_once_with(message)

@pytest.mark.asyncio
@patch("app.api.connection_manager.get_license_plates_by_company")
async def test_broadcast_same_message_twice(mock_get_plates, manager: ConnectionManager):
    mock_get_plates.return_value = ["PLATE-1"]
    websocket = AsyncMock()
    await manager.connect(websocket, ["test_topic"], 1, "PLATE-1")

    message = '{"licensePlateNumber": "PLATE-1"}'
    await manager.broadcast("test_topic", message)
    await manager.broadcast("test_topic", message)

    assert websocket.send_text.call_count == 2
