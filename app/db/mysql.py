from sqlalchemy import create_engine, text
from app.core.config import MYSQL_URI

engine = create_engine(MYSQL_URI, pool_pre_ping=True)

def get_license_plates_by_company(company_id: int) -> list[str]:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id
            FROM trucks
            WHERE company_id = :company_id
        """), {"company_id": company_id})
        return [str(row[0]).strip() for row in result if row[0]]


def get_unit_id_by_tire_id(tire_id: str) -> str | None:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT unit_id
            FROM tires
            WHERE id = :tire_id
        """), {"tire_id": tire_id}).fetchone()
        if result:
            return str(result[0]).strip()
        return None