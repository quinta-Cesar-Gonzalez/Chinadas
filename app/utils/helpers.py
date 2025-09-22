from sqlalchemy import text
from app.db.mysql import engine


def calculate_real_position(license_plate: str, axle: int, wheel: int) -> int | None:
    if axle == 0:
        if wheel == 1:
            return 11
        elif wheel == 2:
            return 12
        return None

    try:
        with engine.connect() as conn:
            res_unit_catalog = conn.execute(
                text("SELECT unit_catalog_id FROM trucks WHERE id = :lp"),
                {"lp": license_plate}
            ).fetchone()

            if not res_unit_catalog or not res_unit_catalog[0]:
                return None

            unit_catalog_id = res_unit_catalog[0]

            catalog_query = text(f"""
                SELECT
                    axles_count,
                    tires_axle_1, tires_axle_2, tires_axle_3, tires_axle_4
                FROM unit_catalog
                WHERE id = :uc_id
            """)

            catalog_info = conn.execute(catalog_query, {"uc_id": unit_catalog_id}).fetchone()

            if not catalog_info:
                return None

            axles_count = catalog_info[0]
            tires_per_axle = catalog_info[1:axles_count + 1]

            position_counter = 1
            mapping = []
            for num_tires in tires_per_axle:
                axle_positions = []
                for _ in range(num_tires):
                    axle_positions.append(position_counter)
                    position_counter += 1
                mapping.append(axle_positions)

            if 1 <= axle <= len(mapping):
                axle_mapping = mapping[axle - 1]
                if 1 <= wheel <= len(axle_mapping):
                    return axle_mapping[wheel - 1]

    except Exception as e:
        print(f"[ERROR] Could not calculate real position for {license_plate}: {e}")
        return None

    return None


def is_unit_authorized(license_plate: str) -> bool:
    if not license_plate:
        return False

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT company_id FROM trucks WHERE unit_identifier = :lp"),
                {"lp": license_plate}
            ).fetchone()
            return result and result[0] == 100
    except Exception as err:
        print(f"[ERROR] Company ID check failed for {license_plate}: {err}")
        return False
