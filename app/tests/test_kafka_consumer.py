import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from app.api.kafka_consumer import (
    handle_gps_message,
    handle_load_message,
    handle_sensor_message,
)

@pytest.fixture
def mock_mongo():
    with patch("app.api.kafka_consumer.mongo_db") as mock_db:
        yield mock_db

# from app.api.kafka_consumer import last_insertion_times

# @pytest.mark.asyncio
# async def test_handle_gps_message_insertion_limit(mock_mongo):
#     vehicle_id = "test_vehicle"
#     parsed_message = {"vehicleId": vehicle_id, "licensePlateNumber": "TEST-PLATE"}

#     await handle_gps_message(parsed_message)
#     mock_mongo.TruckRideLog.insert_one.assert_called_once()

#     await handle_gps_message(parsed_message)
#     mock_mongo.TruckRideLog.insert_one.assert_called_once()

#     insertion_key = (vehicle_id, "TEST-PLATE")
#     last_insertion_times["gps"][insertion_key] = time.time() - 181

#     await handle_gps_message(parsed_message)
#     assert mock_mongo.TruckRideLog.insert_one.call_count == 2

# @pytest.mark.asyncio
# async def test_handle_sensor_message_insertion_limit(mock_mongo):
#     vehicle_id = "test_vehicle"
#     parsed_message = {"vehicleId": vehicle_id, "licensePlateNumber": "TEST-PLATE"}

#     await handle_sensor_message(parsed_message)
#     mock_mongo.Sensors.insert_one.assert_called_once()

#     await handle_sensor_message(parsed_message)
#     mock_mongo.Sensors.insert_one.assert_called_once()

#     insertion_key = (vehicle_id, "TEST-PLATE")
#     last_insertion_times["sensor"][insertion_key] = time.time() - 181

#     await handle_sensor_message(parsed_message)
#     assert mock_mongo.Sensors.insert_one.call_count == 2

# @pytest.mark.asyncio
# async def test_handle_load_message_insertion_limit(mock_mongo):
#     vehicle_id = "test_vehicle"
#     parsed_message = {"vehicleId": vehicle_id, "licensePlateNumber": "TEST-PLATE"}

#     await handle_load_message(parsed_message)
#     mock_mongo.Loads.insert_one.assert_called_once()

#     await handle_load_message(parsed_message)
#     mock_mongo.Loads.insert_one.assert_called_once()

#     insertion_key = (vehicle_id, "TEST-PLATE")
#     last_insertion_times["load"][insertion_key] = time.time() - 181

#     await handle_load_message(parsed_message)
#     assert mock_mongo.Loads.insert_one.call_count == 2
