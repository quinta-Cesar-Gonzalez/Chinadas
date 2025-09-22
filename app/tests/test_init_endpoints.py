import asyncio
from unittest.mock import patch, MagicMock
import pytest
from app.api.init_endpoints import delayed_broadcast, get_initial_gps
import json
from fastapi import BackgroundTasks
from fastapi.responses import Response
from datetime import datetime, timedelta

@pytest.mark.asyncio
@patch("app.api.init_endpoints.manager")
@patch("asyncio.sleep", return_value=None)
async def test_delayed_broadcast_skips_alerts_without_unit_identifier(
    mock_sleep, mock_manager
):
    # Arrange
    mock_manager.broadcast = MagicMock(return_value=asyncio.sleep(0))
    alerts = [
        {"licensePlateNumber": "PLATE-1", "unitIdentifier": "UNIT-1"},
        {"licensePlateNumber": "PLATE-2"},
    ]

    # Act
    await delayed_broadcast(alerts)

    # Assert
    mock_manager.broadcast.assert_called_once()

    # Check that the call was with the correct alert
    args, kwargs = mock_manager.broadcast.call_args

    # The actual message is the second argument (index 1)
    # The first argument is the topic "alerts"
    broadcasted_message = args[1]
    broadcasted_alert = json.loads(broadcasted_message)

    assert broadcasted_alert["unitIdentifier"] == "UNIT-1"
    assert broadcasted_alert["licensePlateNumber"] == "PLATE-1"


@pytest.mark.asyncio
@patch("app.api.init_endpoints.get_license_plates_by_company", return_value=["PLATE-1", "PLATE-2"])
@patch("app.api.init_endpoints.get_initial_data_with_expansion_exhaustive")
@patch("app.api.init_endpoints.get_gps_minutes_since_last_report")
@patch("app.api.init_endpoints.mongo_db")
async def test_get_initial_gps_sets_offline_status_for_timeout(
    mock_mongo, mock_get_gps_minutes, mock_get_initial_data, mock_get_plates
):
    # Arrange
    now = datetime.utcnow()
    old_time = (now - timedelta(minutes=45)).isoformat()
    new_time = (now - timedelta(minutes=15)).isoformat()

    mock_results = [
        {"receiveTime": old_time, "unitStatus": "online", "licensePlateNumber": "PLATE-1", "vehicleId": "VEHICLE-1", "unitIdentifier": "UNIT-1", "spkm": 50},
        {"receiveTime": new_time, "unitStatus": "online", "licensePlateNumber": "PLATE-2", "vehicleId": "VEHICLE-2", "unitIdentifier": "UNIT-2", "spkm": 60},
    ]
    mock_get_initial_data.return_value = mock_results

    def get_minutes_side_effect(receive_time_str):
        if receive_time_str == old_time:
            return 45
        return 15
    mock_get_gps_minutes.side_effect = get_minutes_side_effect

    mock_mongo.Alerts.update_one.return_value = MagicMock()
    background_tasks = BackgroundTasks()

    # Act
    response = await get_initial_gps(cid=1, pn=None, background_tasks=background_tasks)
    response_body = json.loads(response.body)

    # Assert
    assert len(response_body) == 2
    assert response_body[0]["unitStatus"] == "offline"
    assert response_body[0]["licensePlateNumber"] == "PLATE-1"
    assert response_body[0]["spkm"] == 0
    assert response_body[1]["unitStatus"] == "online"
    assert response_body[1]["licensePlateNumber"] == "PLATE-2"
    assert response_body[1]["spkm"] == 60

    # Check that the alert was created with the correct message
    mock_mongo.Alerts.update_one.assert_called_once()
    args, kwargs = mock_mongo.Alerts.update_one.call_args
    alert_doc = args[1]["$set"]
    assert alert_doc["value"] == "No GPS in last 45 minutes"
