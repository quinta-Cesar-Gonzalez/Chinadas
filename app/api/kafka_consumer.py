import json
import logging
import asyncio
import copy
from confluent_kafka import Consumer
from threading import Thread
from app.core.config import KAFKA_CONFIG, SMARTTYRE_CONFIG
from app.core.logger import get_vehicle_logger
from app.db.mysql import engine, get_unit_id_by_tire_id
from app.db.mongo import mongo_db
from app.services.smarttyre_api import SmartTyreAPI
from app.utils.helpers import calculate_real_position
from sqlalchemy import text
import time
import uuid
from app.api.connection_manager import manager

vehicle_data_cache = {}
CACHE_TTL = 60

tire_api = SmartTyreAPI(
    base_url=SMARTTYRE_CONFIG["base_url"],
    client_id=SMARTTYRE_CONFIG["client_id"],
    client_secret=SMARTTYRE_CONFIG["client_secret"],
    sign_key=SMARTTYRE_CONFIG["sign_key"]
)

async def consume_kafka():
    consumer = Consumer(KAFKA_CONFIG)
    topics = ["topic-gps-218", "topic-load-218", "topic-sensor-218"]
    consumer.subscribe(topics)
    logging.info("📡 Kafka subscription started.")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logging.error(f"❌ Kafka error: {msg.error()}")
            continue

        try:
            topic = msg.topic()
            data = msg.value().decode("utf-8")
            parsed = json.loads(data)

            logging.debug(f"📥 Message received on topic '{topic}': {parsed}")

            if topic == "topic-gps-218":
                if parsed.get("trailerLicensePlateNumber"):
                    original_message = copy.deepcopy(parsed)
                    trailer_message = copy.deepcopy(parsed)
                    trailer_message["licensePlateNumber"] = trailer_message["trailerLicensePlateNumber"]
                    await handle_gps_message(original_message)
                    await handle_gps_message(trailer_message)
                else:
                    await handle_gps_message(parsed)
            elif topic == "topic-sensor-218":
                await handle_sensor_message(parsed)
            elif topic == "topic-load-218":
                await handle_load_message(parsed)

            if not (topic == "topic-gps-218" and parsed.get("trailerLicensePlateNumber")):
                parsed.pop("_id", None)
                logging.debug(f"📤 Message sent to WebSocket: {parsed}")

            consumer.commit(asynchronous=False)

        except Exception as e:
            logging.error(f"❌ Kafka processing error: {e}.")

def start_consumer_thread():
    loop = asyncio.new_event_loop()

    def runner():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(consume_kafka())

    thread = Thread(target=runner)
    thread.daemon = True
    thread.start()
    logging.info("🧵 Kafka consumer thread started.")

async def get_vehicle_data(license_plate, vehicle_id):
    """Get vehicle data from cache or fetch from external services."""
    now = time.time()
    if license_plate in vehicle_data_cache and (now - vehicle_data_cache[license_plate]['timestamp']) < CACHE_TTL:
        return vehicle_data_cache[license_plate]['data']

    data = {}
    if license_plate:
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT status, unit_identifier, unit_catalog_id FROM trucks WHERE id = :lp"),
                    {"lp": license_plate}
                ).fetchone()
                if result:
                    data["unitStatus"] = result[0]
                    data["unitIdentifier"] = result[1]
                    data["unitType"] = result[2]
                    logging.info(f"✅ Unit status, unitIdentifier and unitType obtained: {result[0], result[1], result[2]}")
        except Exception as db_err:
            logging.error(f"❌ MySQL query failed: {db_err}")
            data["unitStatus"] = "ERROR"
            data["unitIdentifier"] = "ERROR"
            data["unitType"] = "ERROR"

    if vehicle_id:
        try:
            tires_info = tire_api.get_tires_info_by_vehicle(vehicle_id=vehicle_id)
            if isinstance(tires_info, dict):
                data.update({
                    "latestDataTime": tires_info.get("latestDataTime"),
                    "loadData": tires_info.get("loadData"),
                    "orgId": tires_info.get("orgId"),
                    "totalMileage": tires_info.get("totalMileage"),
                    "tractorName": tires_info.get("tractorName"),
                })
                logging.info(f"✅ SmartTyreAPI data added: {tires_info}")
        except Exception as api_err:
            logging.error(f"❌ SmartTyreAPI error: {api_err}")

    vehicle_data_cache[license_plate] = {'data': data, 'timestamp': now}
    return data

async def handle_gps_message(parsed):
    license_plate = parsed.get("licensePlateNumber")
    vehicle_id = parsed.get("vehicleId")
    receive_time = parsed.get("receiveTime")
    vehicle_logger = get_vehicle_logger(license_plate)
    vehicle_logger.info(f"Received GPS message: {parsed}")

    vehicle_data = await get_vehicle_data(license_plate, vehicle_id)
    parsed.update(vehicle_data)

    filter_query = {"vehicleId": vehicle_id, "receiveTime": receive_time}
    mongo_db.TruckRideLog.update_one(filter_query, {"$set": parsed}, upsert=True)
    vehicle_logger.info(f"💾 Upserted into MongoDB.TruckRideLog: {license_plate}")

    if vehicle_id:
        alert_filter = {
            "vehicleId": vehicle_id,
            "type": "gps_timeout",
            "status": "open"
        }
        update_result = mongo_db.Alerts.update_one(
            alert_filter,
            {"$set": {"status": "closed"}}
        )
        if update_result.modified_count > 0:
            vehicle_logger.info(f"✅ Closed gps_timeout alert for vehicleId: {vehicle_id}")

    parsed.pop("_id", None)
    await manager.broadcast("topic-gps-218", json.dumps(parsed))
    logging.debug(f"📤 Message sent to WebSocket: {parsed}")

async def handle_sensor_message(parsed):
    tyre_code = parsed.get("tyreCode")
    if "trailerLicensePlateNumber" in parsed and parsed["trailerLicensePlateNumber"]:
        if tyre_code:
            unit_id = get_unit_id_by_tire_id(tyre_code)
            if unit_id and unit_id == parsed["trailerLicensePlateNumber"]:
                logging.info(f"🔄 Swapping licensePlateNumber with trailerLicensePlateNumber for tyre {tyre_code}")
                parsed["tractorName"] = parsed["licensePlateNumber"]
                parsed["licensePlateNumber"] = parsed["trailerLicensePlateNumber"]
                del parsed["trailerLicensePlateNumber"]

    axle = parsed.get("axleIndex")
    wheel = parsed.get("wheelIndex")
    license_plate = parsed.get("licensePlateNumber")
    vehicle_id = parsed.get("vehicleId")
    tyre_id = parsed.get("tyreId")
    receive_time = parsed.get("receiveTime")
    vehicle_logger = get_vehicle_logger(license_plate)
    vehicle_logger.info(f"Received sensor message: {parsed}")

    if axle and wheel and license_plate:
        real_pos = calculate_real_position(license_plate, axle, wheel)
        parsed["realPosition"] = real_pos
        if real_pos == 11:
            parsed["spareTireNote"] = "Spare tire 1"
        elif real_pos == 12:
            parsed["spareTireNote"] = "Spare tire 2"
        logging.info(f"🛞 Real position calculated: {real_pos}")

    vehicle_data = await get_vehicle_data(license_plate, vehicle_id)
    parsed.update(vehicle_data)

    pressure = parsed.get("pressure")
    temperature = parsed.get("temperature")

    alerts = []
    if pressure is not None:
        pressure_bar = round(pressure / 6.895, 2)
        parsed["pressure"] = pressure_bar
        if pressure_bar < 90:
            alerts.append({"type": "pressure", "name": "low_pressure", "value": pressure_bar, "tireId": tyre_id})
        elif pressure_bar > 135:
            alerts.append({"type": "pressure", "name": "high_pressure", "value": pressure_bar, "tireId": tyre_id})

    if temperature is not None and temperature > 95:
        alerts.append({"type": "temperature", "name": "high_temperature", "value": temperature, "tireId": tyre_id})

    if alerts:
        parsed["alerts"] = alerts
        for alert in alerts:
            unit_identifier = parsed.get("unitIdentifier")
            if license_plate and unit_identifier:
                alert_doc = {
                    "folio": str(uuid.uuid4())[:8],
                    "status": "open",
                    "type": alert.get("type"),
                    "name": alert.get("name"),
                    "value": alert.get("value"),
                    "tireId": alert.get("tireId"),
                    "licensePlateNumber": license_plate,
                    "vehicleId": vehicle_id,
                    "realPosition": parsed.get("realPosition"),
                    "receiveTime": receive_time,
                    "unitIdentifier": unit_identifier,
                    "unitType": parsed.get("unitType")
                }

                filter_query = {
                    "vehicleId": vehicle_id,
                    "tireId": alert.get("tireId"),
                    "type": alert.get("type"),
                    "name": alert.get("name"),
                    "status": "open"
                }
                mongo_db.Alerts.update_one(filter_query, {"$set": alert_doc}, upsert=True)
                logging.info(f"💾 Upserted sensor alert: {alert_doc}")
                await manager.broadcast("alerts", json.dumps(alert_doc))
            else:
                logging.warning(f"⚠️ Alert not created due to missing licensePlateNumber or unitIdentifier: {license_plate}, {unit_identifier}")

    filter_query = {"vehicleId": vehicle_id, "tyreId": tyre_id, "receiveTime": receive_time}
    mongo_db.Sensors.update_one(filter_query, {"$set": parsed}, upsert=True)
    vehicle_logger.info("💾 Upserted into MongoDB.Sensors")

    parsed.pop("_id", None)
    await manager.broadcast("topic-sensor-218", json.dumps(parsed))
    logging.debug(f"📤 Message sent to WebSocket: {parsed}")

async def handle_load_message(parsed):
    tyre_code = parsed.get("tyreCode")
    license_plate = parsed.get("licensePlateNumber")

    if tyre_code:
        unit_id = get_unit_id_by_tire_id(tyre_code)
        if unit_id and unit_id != license_plate:
            logging.info(f"🔄 Swapping licensePlateNumber with unit_id for tyre {tyre_code}")
            parsed["tractorName"] = license_plate
            parsed["licensePlateNumber"] = unit_id
            license_plate = unit_id

    axle = parsed.get("axleIndex")
    wheel = parsed.get("wheelIndex")
    nowThreadDepth = parsed.get("nowThreadDepth")
    tyre_id = parsed.get("tyreId")
    vehicle_id = parsed.get("vehicleId")
    calculate_time = parsed.get("calculateTime")
    vehicle_logger = get_vehicle_logger(license_plate)
    vehicle_logger.info(f"Received load message: {parsed}")

    if axle and wheel and license_plate:
        real_pos = calculate_real_position(license_plate, axle, wheel)
        parsed["realPosition"] = real_pos
        if real_pos == 11:
            parsed["spareTireNote"] = "Spare tire 1"
        elif real_pos == 12:
            parsed["spareTireNote"] = "Spare tire 2"
        logging.info(f"🛞 Real position (LOAD) calculated: {real_pos}")

    vehicle_data = await get_vehicle_data(license_plate, vehicle_id)
    parsed.update(vehicle_data)

    alerts = []
    if nowThreadDepth is not None and nowThreadDepth < 3:
        alerts.append({
            "type": "depth",
            "name": "low_depth",
            "value": nowThreadDepth,
            "tireId": tyre_id
        })

    if alerts:
        parsed["alerts"] = alerts
        for alert in alerts:
            unit_identifier = parsed.get("unitIdentifier")
            if license_plate and unit_identifier:
                alert_doc = {
                    "folio": str(uuid.uuid4())[:8],
                    "status": "open",
                    "type": alert.get("type"),
                    "name": alert.get("name"),
                    "value": alert.get("value"),
                    "tireId": alert.get("tireId"),
                    "licensePlateNumber": license_plate,
                    "vehicleId": vehicle_id,
                    "realPosition": parsed.get("realPosition"),
                    "receiveTime": parsed.get("receiveTime"),
                    "unitIdentifier": parsed.get("unitIdentifier"),
                }
                filter_query = {
                    "vehicleId": vehicle_id,
                    "tireId": alert.get("tireId"),
                    "type": alert.get("type"),
                    "name": alert.get("name"),
                    "status": "open"
                }
                mongo_db.Alerts.update_one(filter_query, {"$set": alert_doc}, upsert=True)
                logging.info(f"💾 Upserted load alert: {alert_doc}")
                await manager.broadcast("alerts", json.dumps(alert_doc))
            else:
                logging.warning(f"⚠️ Alert not created due to missing licensePlateNumber or unitIdentifier: {license_plate}, {unit_identifier}")

    filter_query = {"vehicleId": vehicle_id, "tyreId": tyre_id, "calculateTime": calculate_time}
    mongo_db.Loads.update_one(filter_query, {"$set": parsed}, upsert=True)
    vehicle_logger.info("💾 Upserted into MongoDB.Loads")

    parsed.pop("_id", None)
    await manager.broadcast("topic-load-218", json.dumps(parsed))
    logging.debug(f"📤 Message sent to WebSocket: {parsed}")
