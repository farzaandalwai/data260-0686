"""Write the cases before measuring embeddings or sweeping thresholds."""

import json
import random
from pathlib import Path

from sqlalchemy import text

from database import db_engine


def main():
    with db_engine.connect() as connection:
        rows = [dict(row._mapping) for row in connection.execute(text(
            "SELECT id AS listing_id,property_title,location,listing_code,available_units FROM rental_listings ORDER BY id LIMIT 70"))]
    cases = []
    for index in range(10):
        seed_id = rows[index]["listing_id"]
        other_id = rows[index + 10]["listing_id"]
        unrelated_id = rows[index + 20]["listing_id"]
        base = f"What is the listing code for rental listing {seed_id}?"
        cases.extend([
            {"case_id": f"exact_{index + 1:02}", "category": "exact", "should_hit": True,
             "listing_id": seed_id, "field": "listing_code", "query": base},
            {"case_id": f"paraphrase_{index + 1:02}", "category": "paraphrase", "should_hit": True,
             "listing_id": seed_id, "field": "listing_code", "query": f"Give me the reference code of rental listing {seed_id}."},
            {"case_id": f"similar_{index + 1:02}", "category": "similar_different", "should_hit": False,
             "listing_id": other_id, "field": "listing_code", "query": f"What is the listing code for rental listing {other_id}?"},
            {"case_id": f"unrelated_{index + 1:02}", "category": "unrelated", "should_hit": False,
             "listing_id": unrelated_id, "field": "location" if index % 2 == 0 else "available_units",
             "query": f"Where is property {unrelated_id} located?" if index % 2 == 0 else f"How many units are available at property {unrelated_id}?"},
        ])
    random.Random(260686).shuffle(cases)
    # JSON is valid YAML, so no parser-specific formatting affects the frozen labels.
    Path("cache_cases.yaml").write_text(json.dumps(cases, indent=2) + "\n")
    Path("hw9_reference.json").write_text(json.dumps({str(row["listing_id"]): row for row in rows}, indent=2) + "\n")
    for name, start, fields in (("training", 30, [["available_units"], ["available_units"], ["available_units"], ["location"]]),
                                ("validation", 34, [["available_units"], ["available_units", "location"], ["location"], ["property_title"], ["listing_code"], ["pet_policy"]]),
                                ("test", 40, [["available_units"], ["location"], ["listing_code"], ["property_title"], ["available_units", "location"], ["pet_policy"], ["available_units"], ["location", "listing_code"]])):
        inputs = []
        for index, requested in enumerate(fields):
            listing_id = rows[start + index]["listing_id"]
            question = f"For rental listing {listing_id}, report {', '.join(requested)} from the supplied record; use null when not recorded."
            inputs.append({"question": question, "listing_id": listing_id, "fields": requested})
        Path(name + "_data.json").write_text(json.dumps(inputs, indent=2) + "\n")
    print("Frozen 40 cases: 10 exact, 10 paraphrase, 10 similar/different, 10 unrelated.")
    print("Created separate reference facts and input-only training/validation/test files.")


if __name__ == "__main__":
    main()
