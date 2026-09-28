import random
import sys

from sqlalchemy import func, select, text

from database import SessionLocal
from models import ListingNote, RentalListing


SEED = 686
LISTING_COUNT = 5000
NOTE_COUNT = 200
EARLY_NOTE_COUNT = 10
LOCATIONS = [
    "San Jose, CA",
    "Santa Clara, CA",
    "Sunnyvale, CA",
    "Campbell, CA",
    "Milpitas, CA",
]


def main():
    random.seed(SEED)
    db = SessionLocal()
    try:
        existing_listings = db.scalar(select(func.count()).select_from(RentalListing))
        existing_notes = db.scalar(select(func.count()).select_from(ListingNote))
        if existing_listings != 0 or existing_notes != 0:
            print("Refusing to seed because experiment tables are not empty")
            print(f"rental_listings={existing_listings}")
            print(f"listing_notes={existing_notes}")
            sys.exit(1)

        db.execute(text("ALTER TABLE rental_listings AUTO_INCREMENT = 1"))
        db.execute(text("ALTER TABLE listing_notes AUTO_INCREMENT = 1"))
        db.commit()

        listings = []
        for number in range(1, LISTING_COUNT + 1):
            listings.append(
                RentalListing(
                    property_title=f"Rental Listing {number:04d}",
                    location=random.choice(LOCATIONS),
                )
            )
        db.add_all(listings)
        db.commit()

        listing_ids = db.scalars(select(RentalListing.id).order_by(RentalListing.id)).all()
        chosen_ids = list(listing_ids[:EARLY_NOTE_COUNT])
        for _ in range(NOTE_COUNT - EARLY_NOTE_COUNT):
            chosen_ids.append(random.choice(listing_ids))

        notes = []
        for number, listing_id in enumerate(chosen_ids, start=1):
            notes.append(
                ListingNote(
                    listing_id=listing_id,
                    note=f"Related note {number:03d}",
                )
            )
        db.add_all(notes)
        db.commit()
        print(f"Seeded rental_listings={LISTING_COUNT} listing_notes={NOTE_COUNT} seed={SEED}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
