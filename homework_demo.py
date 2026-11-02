import json
import time

from hw8_kafka import RAW, read_events, request


SAMPLE = {"propertyTitle": "HW8 San Jose apartment", "location": "San Jose, CA",
          "submitterEmail": "hw8@example.com", "description": "A bright two-bedroom rental near campus.",
          "propertyType": "Apartment", "termsAccepted": True}


def main():
    created = request("CREATE_LISTING", SAMPLE)
    assert created["success"], created
    fetched = request("GET_LISTING", {"listing_id": created["listing_id"]})
    assert fetched["success"] and fetched["listing"]["propertyTitle"] == SAMPLE["propertyTitle"]
    time.sleep(0.2)
    ids = [created["correlation_id"], fetched["correlation_id"]]
    flow = read_events()
    flow = [row for row in flow if row.get("correlation_id") in ids]
    flow.sort(key=lambda row: (ids.index(row["correlation_id"]), row["timestamp"]))
    result = {"create": created, "get": fetched, "flow": flow, "correlation_preserved": all(row["message"]["correlation_id"] == row["correlation_id"] for row in flow if "message" in row)}
    (RAW / "round_trip.json").write_text(json.dumps(result, indent=2))
    print("CREATE_LISTING -> GET_LISTING; correlation IDs preserved:", result["correlation_preserved"])


if __name__ == "__main__":
    main()
