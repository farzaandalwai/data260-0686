import hashlib
import json

from sqlalchemy import text

from database import db_engine


def database_digest():
    with db_engine.connect() as connection:
        rows = [dict(row._mapping) for row in connection.execute(text("SELECT id,property_title,location,listing_code,available_units,property_manager_id,created_at,updated_at FROM rental_listings ORDER BY id"))]
    encoded = json.dumps(rows, sort_keys=True, default=str).encode()
    return {"rows": len(rows), "sha256": hashlib.sha256(encoded).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(database_digest()))
