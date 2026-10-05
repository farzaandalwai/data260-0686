import argparse

from sqlalchemy import inspect, text

from database import db_engine


INITIAL_EMAIL = "hw5-manager@example.com"
NEW_COLUMNS = {
    "listing_code": "VARCHAR(50) NULL",
    "available_units": "INT NULL DEFAULT 1",
    "property_manager_id": "INT NULL",
    "created_at": "DATETIME NULL",
    "updated_at": "DATETIME NULL",
}


def show_plan(conn):
    if conn.scalar(text("SELECT DATABASE()")) != "s0686_rel":
        raise RuntimeError("Expected database s0686_rel")
    for table in ["rental_listings", "listing_notes"]:
        count = conn.scalar(text(f"SELECT COUNT(*) FROM {table}"))
        print(table, "rows:", count)
    columns = {column["name"] for column in inspect(conn).get_columns("rental_listings")}
    print("Missing listing columns:", sorted(set(NEW_COLUMNS) - columns))
    print("Create property_managers if missing; preserve all existing listing and note rows.")
    print("Backfill missing codes as RH-0686- followed by the listing ID padded to 5 digits.")
    print("Assign unassigned listings to Initial Manager; backfill units and UTC timestamps.")
    print("Then add non-null, unique, nonnegative-units, and RESTRICT foreign-key constraints.")


def migrate(conn):
    before = {
        table: conn.scalar(text(f"SELECT COUNT(*) FROM {table}"))
        for table in ["rental_listings", "listing_notes"]
    }
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS property_managers (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT uq_property_managers_email UNIQUE (email)
        ) ENGINE=InnoDB
    """))
    columns = {column["name"] for column in inspect(conn).get_columns("rental_listings")}
    for name, definition in NEW_COLUMNS.items():
        if name not in columns:
            conn.execute(text(f"ALTER TABLE rental_listings ADD COLUMN {name} {definition}"))

    manager_id = conn.scalar(text("SELECT id FROM property_managers WHERE email = :email"), {"email": INITIAL_EMAIL})
    if manager_id is None:
        result = conn.execute(text("""
            INSERT INTO property_managers (first_name, last_name, email)
            VALUES ('Initial', 'Manager', :email)
        """), {"email": INITIAL_EMAIL})
        manager_id = result.lastrowid

    conn.execute(text("""
        UPDATE rental_listings
        SET listing_code = CONCAT('RH-0686-', LPAD(id, GREATEST(5, CHAR_LENGTH(id)), '0'))
        WHERE listing_code IS NULL
    """))
    conn.execute(text("UPDATE rental_listings SET property_manager_id = :manager_id WHERE property_manager_id IS NULL"), {"manager_id": manager_id})
    conn.execute(text("UPDATE rental_listings SET available_units = 1 WHERE available_units IS NULL"))
    conn.execute(text("UPDATE rental_listings SET created_at = UTC_TIMESTAMP() WHERE created_at IS NULL"))
    conn.execute(text("UPDATE rental_listings SET updated_at = created_at WHERE updated_at IS NULL"))

    invalid = conn.scalar(text("""
        SELECT COUNT(*) FROM rental_listings r
        LEFT JOIN property_managers m ON m.id = r.property_manager_id
        WHERE r.available_units < 0 OR m.id IS NULL
           OR r.listing_code NOT REGEXP '^RH-0686-[0-9]{5,}$'
    """))
    duplicates = conn.scalar(text("""
        SELECT COUNT(*) FROM (
            SELECT listing_code FROM rental_listings GROUP BY listing_code HAVING COUNT(*) > 1
        ) duplicate_codes
    """))
    if invalid or duplicates:
        raise RuntimeError("Invalid existing HW5 values; constraints were not finalized")

    conn.execute(text("""
        ALTER TABLE rental_listings
        MODIFY listing_code VARCHAR(50) NOT NULL,
        MODIFY available_units INT NOT NULL DEFAULT 1,
        MODIFY property_manager_id INT NOT NULL,
        MODIFY created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        MODIFY updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    """))
    indexes = inspect(conn).get_indexes("rental_listings")
    if not any(index["unique"] and index["column_names"] == ["listing_code"] for index in indexes):
        conn.execute(text("ALTER TABLE rental_listings ADD CONSTRAINT uq_rental_listings_code UNIQUE (listing_code)"))
    foreign_keys = inspect(conn).get_foreign_keys("rental_listings")
    manager_keys = [key for key in foreign_keys if key["constrained_columns"] == ["property_manager_id"]]
    if not manager_keys:
        conn.execute(text("""
            ALTER TABLE rental_listings ADD CONSTRAINT fk_listing_manager
            FOREIGN KEY (property_manager_id) REFERENCES property_managers(id) ON DELETE RESTRICT
        """))
    elif any(key["referred_table"] != "property_managers" or key.get("options", {}).get("ondelete", "RESTRICT") not in ["RESTRICT", "NO ACTION"] for key in manager_keys):
        raise RuntimeError("Existing manager foreign key does not use RESTRICT")
    checks = inspect(conn).get_check_constraints("rental_listings")
    if not any(check["name"] == "ck_available_units" for check in checks):
        conn.execute(text("ALTER TABLE rental_listings ADD CONSTRAINT ck_available_units CHECK (available_units >= 0)"))
    for table, count in before.items():
        after = conn.scalar(text(f"SELECT COUNT(*) FROM {table}"))
        if after != count:
            raise RuntimeError(f"Row count changed for {table}")
        print(table, "preserved rows:", after)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        with db_engine.connect() as conn:
            show_plan(conn)
            if not args.apply:
                print("Read-only plan. Run with --apply only after migration approval.")
                return
            migrate(conn)
            conn.commit()
            print("HW5 migration complete")
    except Exception as error:
        print("Migration stopped:", type(error).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
