"""Idempotently keep one stable Part 1 rental document for screenshots."""

from datetime import datetime, timezone
import json

from hw6_config import ROOT
from hw6_mongo import get_collection


TITLE = "Santa Clara Light Rail Apartment"


def main() -> None:
    collection = get_collection("rental_documents")
    now = datetime.now(timezone.utc)
    collection.update_one(
        {"title": TITLE},
        {
            "$set": {
                "description": "Stable HW6 evidence listing near light rail with in-unit laundry.",
                "status": "available",
                "property_type": "apartment",
                "available_from": datetime(2026, 12, 1, 17, 0, tzinfo=timezone.utc),
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    document = collection.find_one({"title": TITLE})
    output = {
        "id": str(document["_id"]),
        "title": document["title"],
        "description": document["description"],
        "status": document["status"],
        "property_type": document["property_type"],
        "available_from": document["available_from"].isoformat(),
        "created_at": document["created_at"].isoformat(),
        "updated_at": document["updated_at"].isoformat(),
    }
    path = ROOT / "reports" / "hw06" / "raw" / "stable_sample_document.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
