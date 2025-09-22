import json
import uuid
import logging
import re
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from app.db.mongo import mongo_db
from app.db.mysql import get_license_plates_by_company
from app.api.connection_manager import manager

router = APIRouter()
MAX_ALERTS = 500

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def get_gps_minutes_since_last_report(receive_time_str: str) -> int | None:
    try:
        receive_time = datetime.fromisoformat(receive_time_str)
        delta = datetime.utcnow() - receive_time
        return int(delta.total_seconds() / 60)
    except Exception as e:
        logging.warning(f"⚠️ GPS Timeout Error: {e}")
        return None

def clean_surrogates(s: str) -> str:
    return re.sub(r'[\ud800-\udfff]', '?', s)

def clean_entry(entry: dict) -> dict:
    entry.pop("_id", None)
    entry["source"] = "initial"
    for k, v in entry.items():
        if isinstance(v, str):
            entry[k] = clean_surrogates(v)
    return entry

async def get_initial_data_with_expansion(collection, pipeline_builder, license_plates=None, plate_field="licensePlateNumber"):
    time_windows = [5, 15, 30, 60, 90, 365]

    for days in time_windows:
        limit_date = datetime.utcnow() - timedelta(days=days)
        pipeline = pipeline_builder(limit_date, license_plates)

        logging.info(f"🕵 Executing search for the last {days} days")

        entries = list(collection.aggregate(pipeline, allowDiskUse=True))
        logging.info(f"From {days} days ago, documents obtained from Mongo: {len(entries)}")

        if entries:
            filtered = [clean_entry(e) for e in entries if e.get(plate_field)]
            logging.info(f"✅ Documents after filtering plates: {len(filtered)}")

            if filtered:
                logging.info(f"✅ Data found in the last {days} days. Total documents: {len(filtered)}")
                return filtered
            else:
                logging.info(f"⚠️ No useful documents in the last {days} days, trying next window.")
        else:
            logging.info(f"No documents found for the last {days} days, trying next window.")

    logging.warning(f"❌ No useful documents found in any of the time windows up to {time_windows[-1]} days")
    return []

async def get_initial_data_with_expansion_exhaustive(collection, pipeline_builder, license_plates=None, plate_field="licensePlateNumber"):
    time_windows = [5, 15, 30, 60, 90, 365]
    found_results = {}

    plates_to_find = set(license_plates) if license_plates is not None else None

    for days in time_windows:
        if plates_to_find is not None and not plates_to_find:
            logging.info("✅ All target plates found. Stopping search.")
            break

        limit_date = datetime.utcnow() - timedelta(days=days)

        plates_list_for_pipeline = list(plates_to_find) if plates_to_find is not None else None

        pipeline = pipeline_builder(limit_date, plates_list_for_pipeline)

        if license_plates is None and found_results:
            if pipeline and "$match" in pipeline[0]:
                pipeline[0]["$match"][plate_field] = {"$nin": list(found_results.keys())}
            else:
                pipeline.insert(0, {"$match": {plate_field: {"$nin": list(found_results.keys())}}})

        logging.info(f"🕵️ Executing search for {'all remaining' if plates_list_for_pipeline is None else len(plates_list_for_pipeline)} plates in the last {days} days.")

        try:
            entries = list(collection.aggregate(pipeline, allowDiskUse=True))
            logging.info(f"From {days} days ago, documents obtained from Mongo: {len(entries)}")

            if entries:
                filtered = [clean_entry(e) for e in entries if e.get(plate_field)]

                if filtered:
                    newly_found_count = 0
                    for entry in filtered:
                        plate = entry.get(plate_field)
                        if plate and plate not in found_results:
                            found_results[plate] = entry
                            newly_found_count += 1
                            if plates_to_find is not None:
                                plates_to_find.discard(plate)

                    logging.info(f"✅ Found {newly_found_count} new plates. Total found: {len(found_results)}")

        except Exception as e:
            logging.error(f"❌ Error during aggregation for last {days} days: {e}")
            continue

    final_list = list(found_results.values())
    if not final_list:
        logging.warning(f"❌ No useful documents found in any of the time windows up to {time_windows[-1]} days")
    else:
        logging.info(f"✅ Total unique documents found: {len(final_list)}")

    return final_list

async def delayed_broadcast(alerts: list):
    """Waits 3 seconds, then broadcasts a list of alerts with a 0.5-second delay between each."""
    await asyncio.sleep(3)
    for alert in alerts:
        if alert.get("unitIdentifier"):
            alert_str = json.dumps(alert)
            await manager.broadcast("alerts", alert_str)
            logging.info(f"📤 Delayed GPS Timeout alert broadcasted for plate {alert.get('licensePlateNumber')}")
            await asyncio.sleep(0.5)
        else:
            logging.warning(f"⚠️ Delayed GPS Timeout alert for plate {alert.get('licensePlateNumber')} not broadcasted due to missing unitIdentifier.")


@router.get("/init/gps")
async def get_initial_gps(
    licensePlateNumber: str = Query(default=None),
    pn: list[str] = Query(default=None, alias="pn"),
    cid: int = Query(default=None, alias="cid"),
    background_tasks: BackgroundTasks = None
):
    try:
        if cid == 2:
            licensePlates = None
        elif cid and not licensePlateNumber and not pn:
            licensePlates = get_license_plates_by_company(cid)
        else:
            licensePlates = pn
        
        if cid != 2 and licensePlates is not None and len(licensePlates) == 0:
            return Response(content=json.dumps([], ensure_ascii=False), media_type="application/json")

        def pipeline_builder(limit_date, plates):
            match = {"receiveTime": {"$gte": limit_date.isoformat()}}
            if licensePlateNumber:
                match["licensePlateNumber"] = licensePlateNumber.strip()
            elif plates:
                match["licensePlateNumber"] = {"$in": plates}
            return [
                {"$match": match},
                {"$sort": {"licensePlateNumber": 1, "receiveTime": -1}},
                {"$group": {"_id": "$licensePlateNumber", "doc": {"$first": "$$ROOT"}}},
                {"$replaceRoot": {"newRoot": "$doc"}}
            ]

        results = await get_initial_data_with_expansion_exhaustive(mongo_db.TruckRideLog, pipeline_builder, licensePlates)

        alerts_to_broadcast = []

        for r in results:
            minutes_since_report = get_gps_minutes_since_last_report(r.get("receiveTime"))
            if minutes_since_report is not None and minutes_since_report > 30:
                r["unitStatus"] = "offline"
                r["spkm"] = 0
                plate = r.get("licensePlateNumber")
                vehicle_id = r.get("vehicleId")
                alert_doc = {
                    "folio": str(uuid.uuid4())[:8],
                    "status": "open",
                    "type": "gps",
                    "name": "gps_timeout",
                    "value": minutes_since_report,
                    "licensePlateNumber": plate,
                    "vehicleId": vehicle_id,
                    "receiveTime": r.get("receiveTime"),
                    "companyId": cid,
                    "unitIdentifier": r.get("unitIdentifier")
                }
                filter_query = {
                    "vehicleId": vehicle_id,
                    "type": "gps",
                    "name": "gps_timeout",
                    "status": "open"
                }
                mongo_db.Alerts.update_one(filter_query, {"$set": alert_doc}, upsert=True)

                alerts_to_broadcast.append(alert_doc)
                logging.info(f"📤 GPS Timeout alert generated for plate {plate}. Broadcasting will be delayed.")

        if alerts_to_broadcast:
            background_tasks.add_task(delayed_broadcast, alerts_to_broadcast)

        return Response(content=json.dumps(results, ensure_ascii=False), media_type="application/json")
    except Exception as e:
        logging.error(f"❌ Error in /init/gps: {e}")
        return JSONResponse(status_code=500, content={"error": f"GPS Error: {str(e)}"})

@router.get("/init/sensor")
async def get_initial_sensor(
    licensePlateNumber: str = Query(default=None),
    pn: list[str] = Query(default=None, alias="pn"),
    cid: int = Query(default=None, alias="cid")
):
    try:
        if cid == 2:
            licensePlates = None
        elif cid and not licensePlateNumber and not pn:
            licensePlates = get_license_plates_by_company(cid)
        else:
            licensePlates = pn

        if cid != 2 and licensePlates is not None and len(licensePlates) == 0:
            return Response(content=json.dumps([], ensure_ascii=False), media_type="application/json")

        def pipeline_builder(limit_date, plates):
            match = {"receiveTime": {"$gte": limit_date.isoformat()}}
            if licensePlateNumber:
                match["licensePlateNumber"] = licensePlateNumber.strip()
            elif plates:
                match["licensePlateNumber"] = {"$in": plates}
            return [
                {"$match": match},
                {"$sort": {
                    "vehicleId": 1,
                    "licensePlateNumber": 1,
                    "realPosition": 1,
                    "receiveTime": -1
                }},
                {"$group": {
                    "_id": {
                        "vehicleId": "$vehicleId",
                        "licensePlateNumber": "$licensePlateNumber",
                        "realPosition": "$realPosition"
                    },
                    "doc": {"$first": "$$ROOT"}
                }},
                {"$replaceRoot": {"newRoot": "$doc"}}
            ]

        results = await get_initial_data_with_expansion(mongo_db.Sensors, pipeline_builder, licensePlates)
        return Response(content=json.dumps(results, ensure_ascii=False), media_type="application/json")
    except Exception as e:
        logging.error(f"❌ Error in /init/sensor: {e}")
        return JSONResponse(status_code=500, content={"error": f"Sensor Error: {str(e)}"})

@router.get("/init/load")
async def get_initial_load(
    licensePlateNumber: str = Query(default=None),
    pn: list[str] = Query(default=None, alias="pn"),
    cid: int = Query(default=None, alias="cid")
):
    try:
        if cid == 2:
            licensePlates = None
        elif cid and not licensePlateNumber and not pn:
            licensePlates = get_license_plates_by_company(cid)
        else:
            licensePlates = pn

        if cid != 2 and licensePlates is not None and len(licensePlates) == 0:
            return Response(content=json.dumps([], ensure_ascii=False), media_type="application/json")

        def pipeline_builder(limit_date, plates):
            match = {"calculateTime": {"$gte": limit_date.isoformat()}}
            if licensePlateNumber:
                match["licensePlateNumber"] = licensePlateNumber.strip()
            elif plates:
                match["licensePlateNumber"] = {"$in": plates}
            return [
                {"$match": match},
                {"$sort": {
                    "vehicleId": 1,
                    "licensePlateNumber": 1,
                    "realPosition": 1,
                    "calculateTime": -1
                }},
                {"$group": {
                    "_id": {
                        "vehicleId": "$vehicleId",
                        "licensePlateNumber": "$licensePlateNumber",
                        "realPosition": "$realPosition"
                    },
                    "doc": {"$first": "$$ROOT"}
                }},
                {"$replaceRoot": {"newRoot": "$doc"}}
            ]

        results = await get_initial_data_with_expansion(mongo_db.Loads, pipeline_builder, licensePlates)
        return Response(content=json.dumps(results, ensure_ascii=False), media_type="application/json")
    except Exception as e:
        logging.error(f"❌ Error in /init/load: {e}")
        return JSONResponse(status_code=500, content={"error": f"Load Error: {str(e)}"})

def get_latest_documents(collection_name, vehicle_identifiers, time_field):
    if not vehicle_identifiers:
        return {}

    collection = mongo_db[collection_name]

    match_conditions = [
        {
            "vehicleId": vid,
            "licensePlateNumber": lp,
            "realPosition": rp
        } for vid, lp, rp in vehicle_identifiers if vid and lp and rp
    ]

    if not match_conditions:
        return {}

    pipeline = [
        {"$match": {"$or": match_conditions}},
        {"$sort": {time_field: -1}},
        {"$group": {
            "_id": {
                "vehicleId": "$vehicleId",
                "licensePlateNumber": "$licensePlateNumber",
                "realPosition": "$realPosition"
            },
            "doc": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$doc"}}
    ]

    latest_docs = list(collection.aggregate(pipeline, allowDiskUse=True))

    lookup = {}
    for doc in latest_docs:
        key = (doc.get("vehicleId"), doc.get("licensePlateNumber"), doc.get("realPosition"))
        lookup[key] = doc
    return lookup

@router.get("/init/alerts")
async def get_initial_alerts(
    licensePlateNumber: str = Query(default=None),
    pn: list[str] = Query(default=None, alias="pn"),
    cid: int = Query(default=None, alias="cid")
):
    try:
        if cid == 2:
            licensePlates = None
        elif cid and not licensePlateNumber and not pn:
            licensePlates = get_license_plates_by_company(cid)
        else:
            licensePlates = pn

        if cid != 2 and licensePlates is not None and len(licensePlates) == 0:
            return Response(content=json.dumps([], ensure_ascii=False), media_type="application/json")

        filters = {
            "licensePlateNumber": {"$ne": None},
            "status": "open"
        }

        if licensePlateNumber:
            filters["licensePlateNumber"] = licensePlateNumber.strip()
        elif licensePlates:
            filters["licensePlateNumber"] = {"$in": licensePlates}

        alerts_from_db = list(mongo_db.Alerts.find(filters).sort("receiveTime", -1).limit(MAX_ALERTS))

        vehicle_identifiers = set()
        for alert in alerts_from_db:
            vehicle_identifiers.add((
                alert.get("vehicleId"),
                alert.get("licensePlateNumber"),
                alert.get("realPosition")
            ))

        latest_sensors = get_latest_documents("Sensors", list(vehicle_identifiers), "receiveTime")
        latest_loads = get_latest_documents("Loads", list(vehicle_identifiers), "calculateTime")

        active_alerts_set = set()
        for key, doc in latest_sensors.items():
            for embedded_alert in doc.get("alerts", []):
                alert_type = embedded_alert.get("type")
                alert_name = embedded_alert.get("name")
                if alert_type and alert_name:
                    active_alerts_set.add(key + (alert_type, alert_name))

        for key, doc in latest_loads.items():
            for embedded_alert in doc.get("alerts", []):
                alert_type = embedded_alert.get("type")
                alert_name = embedded_alert.get("name")
                if alert_type and alert_name:
                    active_alerts_set.add(key + (alert_type, alert_name))

        final_alerts = []
        seen_alerts = set()

        for alert in alerts_from_db:
            try:
                vehicle_id = alert.get("vehicleId")
                plate = alert.get("licensePlateNumber")
                real_position = alert.get("realPosition")
                alert_type = alert.get("type")
                alert_name = alert.get("name")
                tire_id = alert.get("tireId")

                alert_key = (vehicle_id, tire_id, alert_type, alert_name, real_position)
                if alert_key in seen_alerts:
                    continue
                seen_alerts.add(alert_key)

                liveness_key = (vehicle_id, plate, real_position, alert_type, alert_name)

                if liveness_key not in active_alerts_set:
                    mongo_db.Alerts.update_one({"_id": alert["_id"]}, {"$set": {"status": "closed"}})
                    continue

                alert_clean = {
                    "type": alert_type,
                    "name": alert_name,
                    "value": alert.get("value"),
                    "tireId": tire_id,
                    "licensePlateNumber": plate,
                    "vehicleId": vehicle_id,
                    "realPosition": real_position,
                    "receiveTime": alert.get("receiveTime"),
                    "unitIdentifier": alert.get("unitIdentifier"),
                    "status": "open",
                    "folio": alert.get("folio")
                }
                final_alerts.append(alert_clean)

            except Exception as err:
                logging.warning(f"⚠️ Error processing alert: {err}")
                continue

        return Response(content=json.dumps(final_alerts, ensure_ascii=False), media_type="application/json")

    except Exception as e:
        logging.error(f"❌ Error in /init/alerts: {e}")
        return JSONResponse(status_code=500, content={"error": f"Alerts Error: {str(e)}"})
