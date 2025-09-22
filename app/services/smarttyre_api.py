import json
import time
import secrets
import requests
from app.services.sign_util import SignUtil

class SmartTyreAPI:
    """
    Client to interact with the Smart Tyre API.
    """

    def __init__(self, base_url, client_id, client_secret, sign_key):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.sign_key = sign_key

    def _new_header(self, need_access_token=True):
        headers = {
            "clientId": self.client_id,
            "timestamp": str(int(time.time() * 1000)),
            "nonce": secrets.token_hex(16),
        }

        if need_access_token:
            headers["accessToken"] = self.get_access_token()

        return headers

    def _new_signature(self, headers, body, params, paths):
        return SignUtil.sign(
            headers=headers,
            body=body,
            params=params,
            paths=paths,
            sign_key=self.sign_key
        )

    def _new_get_request(self, endpoint, params):
        url = f"{self.base_url}{endpoint}"
        headers = self._new_header()
        headers["sign"] = self._new_signature(headers, "", params, [])
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        response = requests.get(url, headers=headers, params=params, timeout=20)
        if response.status_code == 200:
            return response.json().get("data")
        return None

    def _new_post_request(self, endpoint, body, need_access_token=True, returns_data=True):
        url = f"{self.base_url}{endpoint}"
        headers = self._new_header(need_access_token)
        headers["sign"] = self._new_signature(headers, body, {}, [])
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        response = requests.post(url, headers=headers, data=body, timeout=20)
        if response.status_code == 200:
            return response.json().get("data") if returns_data else response.json().get("msg")
        return None

    def get_access_token(self):
        endpoint = "/smartyre/openapi/auth/oauth20/authorize"
        body = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "grantType": "client_credentials",
        }
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)

        response = self._new_post_request(
            endpoint=endpoint,
            body=body_str,
            need_access_token=False
        )

        return response.get("accessToken") if response else None

    # ----------------- VEHICLE -----------------

    def get_vehicle_list(self):
        return self._new_get_request("/smartyre/openapi/vehicle/list", params={})

    def get_vehicle_info(self, vehicle_id):
        if not vehicle_id:
            return None
        params = { "vehicleId": [str(vehicle_id)] }
        return self._new_get_request("/smartyre/openapi/vehicle/detail", params)

    def add_vehicle(self, vehicle_info):
        body_str = json.dumps(vehicle_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/vehicle/insert", body=body_str, returns_data=False)

    def update_vehicle(self, vehicle_info):
        body_str = json.dumps(vehicle_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/vehicle/update", body=body_str, returns_data=False)

    # ----------------- TIRE -----------------

    def get_tire_list(self):
        return self._new_get_request("/smartyre/openapi/tyre/list", params={})

    def get_tire_info(self, tire_id):
        params = { "id": [str(tire_id)] }
        return self._new_get_request("/smartyre/openapi/tyre/detail", params)

    def add_tire(self, tire_info):
        body_str = json.dumps(tire_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/tyre/insert", body=body_str, returns_data=False)

    def update_tire(self, tire_info):
        body_str = json.dumps(tire_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/tyre/update", body=body_str, returns_data=False)

    def get_tires_info_by_vehicle(self, vehicle_id):
        if not vehicle_id:
            return None
        body_str = json.dumps({ "vehicleId": vehicle_id }, separators=(",", ":"))
        return self._new_post_request("/smartyre/openapi/vehicle/tyre/data", body=body_str)

    def bind_tire_to_vehicle(self, vehicle_id, tire_code, axle_index, wheel_index):
        body = {
            "vehicleId": vehicle_id,
            "tyreCode": tire_code,
            "axleIndex": axle_index,
            "wheelIndex": wheel_index
        }
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/vehicle/tyre/bind", body=body_str, returns_data=False)

    def unbind_tire_from_vehicle(self, vehicle_id, tire_id):
        body = {
            "vehicleId": vehicle_id,
            "tyreCode": tire_id,
        }
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/vehicle/tyre/unbind", body=body_str, returns_data=False)

    # ----------------- SENSOR -----------------

    def get_sensor_list(self):
        return self._new_get_request("/smartyre/openapi/sensor/list", params={})

    def get_sensor_info(self, sensor_id):
        params = { "id": [str(sensor_id)] }
        return self._new_get_request("/smartyre/openapi/sensor/detail", params)

    def add_sensor(self, sensor_info):
        body_str = json.dumps(sensor_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/sensor/insert", body=body_str, returns_data=False)

    def update_sensor(self, sensor_info):
        body_str = json.dumps(sensor_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/sensor/update", body=body_str, returns_data=False)

    def bind_sensor_to_tire(self, tire_code, vehicle_id, axle_index, wheel_index, sensor_code):
        body = {
            "tyreCode": tire_code,
            "vehicleId": vehicle_id,
            "axleIndex": axle_index,
            "wheelIndex": wheel_index,
            "sensorCode": sensor_code
        }
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/tyre/sensor/bind", body=body_str, returns_data=False)

    def unbind_sensor_from_tire(self, tire_code, vehicle_id, axle_index, wheel_index, sensor_code):
        body = {
            "tyreCode": tire_code,
            "vehicleId": vehicle_id,
            "axleIndex": axle_index,
            "wheelIndex": wheel_index,
            "sensorCode": sensor_code
        }
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/tyre/sensor/unbind", body=body_str, returns_data=False)

    # ----------------- TBOX -----------------

    def get_tboxes_list(self):
        return self._new_get_request("/smartyre/openapi/tbox/list", params={})

    def get_tbox_info(self, tbox_id):
        params = { "id": [str(tbox_id)] }
        return self._new_get_request("/smartyre/openapi/tbox/detail", params)

    def add_tbox(self, tbox_info):
        body_str = json.dumps(tbox_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/tbox/insert", body=body_str, returns_data=False)

    def update_tbox(self, tbox_info):
        body_str = json.dumps(tbox_info, separators=(",", ":"), ensure_ascii=False)
        return self._new_post_request("/smartyre/openapi/tbox/update", body=body_str, returns_data=False)

    # ----------------- Reference Data -----------------

    def get_tire_brands(self):
        return self._new_get_request("/smartyre/openapi/tyre/brand/all", params={})

    def get_tire_sizes(self):
        return self._new_get_request("/smartyre/openapi/tyre/size/all", params={})

    def get_vehicle_models(self):
        return self._new_get_request("/smartyre/openapi/vehicle/model/all", params={})

    def get_axle_types(self):
        return self._new_get_request("/smartyre/openapi/vehicle/axle/all", params={})
