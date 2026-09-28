from sqlalchemy import text

from database import db_session_basede26


INDEX_NAME = "idx_rental_listings_property_title"


def index_exists(connection):
    rows = connection.execute(text("SHOW INDEX FROM rental_listings")).mappings()
    return any(row["Key_name"] == INDEX_NAME for row in rows)


with db_session_basede26.connect() as connection:
    exists = index_exists(connection)

if exists:
    print("HW4 index already exists")
else:
    with db_session_basede26.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX idx_rental_listings_property_title "
                "ON rental_listings(property_title)"
            )
        )
    print("HW4 index created")
