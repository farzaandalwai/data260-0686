import json

from hw5_agent import MockModel
from hw5_agent import run_agent
from hw5_tool_runtime import execute_tool


LISTINGS = {
    1: {
        "id": 1,
        "property_title": "San Jose Apartment",
        "location": "San Jose, CA",
        "available_units": 2,
        "property_manager_id": 1,
    },
    2: {
        "id": 2,
        "property_title": "Closed Milpitas Rental",
        "location": "Milpitas, CA",
        "available_units": 0,
        "property_manager_id": 1,
    },
}


def fake_search(query, limit=10):
    if not str(query).strip():
        return {"ok": False, "data": None, "error": "query must not be blank."}
    if not 1 <= int(limit) <= 25:
        return {"ok": False, "data": None, "error": "limit must be between 1 and 25."}
    matches = [
        item for item in LISTINGS.values()
        if query.lower() in item["location"].lower() or query.lower() in item["property_title"].lower()
    ]
    return {"ok": True, "data": matches[:int(limit)], "error": None}


def fake_detail(listing_id):
    if int(listing_id) <= 0:
        return {"ok": False, "data": None, "error": "listing_id must be positive."}
    listing = LISTINGS.get(int(listing_id))
    if listing is None:
        return {"ok": False, "data": None, "error": "Rental listing not found."}
    return {"ok": True, "data": dict(listing), "error": None}


def fake_aggregate(manager_id):
    if int(manager_id) <= 0:
        return {"ok": False, "data": None, "error": "manager_id must be positive."}
    rows = [item for item in LISTINGS.values() if item["property_manager_id"] == int(manager_id)]
    return {
        "ok": True,
        "data": {
            "manager_id": int(manager_id),
            "first_name": "Initial",
            "last_name": "Manager",
            "listing_count": len(rows),
            "total_available_units": sum(item["available_units"] for item in rows),
        },
        "error": None,
    }


TOOLS = {
    "search_listings": fake_search,
    "detail_lookup": fake_detail,
    "aggregate_by_manager": fake_aggregate,
}


def call(name, inputs):
    return json.loads(execute_tool(name, inputs, tools=TOOLS))


def test_search_valid():
    result = call("search_listings", {"query": "San Jose", "limit": 5})
    assert result["ok"] is True
    assert result["error"] is None
    assert result["data"][0]["id"] == 1


def test_search_invalid():
    result = call("search_listings", {"query": "", "limit": 5})
    assert result == {"ok": False, "data": None, "error": "query must not be blank."}


def test_detail_valid():
    result = call("detail_lookup", {"listing_id": 1})
    assert result["ok"] is True
    assert result["data"]["available_units"] == 2


def test_detail_invalid():
    result = call("detail_lookup", {"listing_id": -1})
    assert result == {"ok": False, "data": None, "error": "listing_id must be positive."}


def test_aggregate_valid():
    result = call("aggregate_by_manager", {"manager_id": 1})
    assert result["ok"] is True
    assert result["data"]["listing_count"] == 2
    assert result["data"]["total_available_units"] == 2


def test_aggregate_invalid():
    result = call("aggregate_by_manager", {"manager_id": 0})
    assert result == {"ok": False, "data": None, "error": "manager_id must be positive."}


def test_unknown_tool():
    result = call("delete_listing", {"listing_id": 1})
    assert result == {"ok": False, "data": None, "error": "Unknown tool."}


def test_safety_blocks_unavailable():
    allowed = call("detail_lookup", {"listing_id": 1})
    blocked = call("detail_lookup", {"listing_id": 2})
    assert allowed["ok"] is True
    assert allowed["data"]["available_units"] == 2
    assert blocked == {"ok": False, "data": None, "error": "Listing is unavailable"}


def test_mock_agent_max_steps():
    result = run_agent(
        "Find rentals in San Jose.",
        model=MockModel(),
        max_steps=2,
        execute=lambda name, inputs: execute_tool(name, inputs, tools=TOOLS),
        scenario="offline_max_steps",
    )
    assert result["stop_reason"] == "max_steps"
    assert len(result["steps"]) == 2
    assert result["tool_calls"] == 2


TESTS = [
    ("search valid", test_search_valid),
    ("search invalid", test_search_invalid),
    ("detail valid", test_detail_valid),
    ("detail invalid", test_detail_invalid),
    ("aggregate valid", test_aggregate_valid),
    ("aggregate invalid", test_aggregate_invalid),
    ("unknown tool", test_unknown_tool),
    ("safety blocks unavailable listing", test_safety_blocks_unavailable),
    ("mock agent reaches max_steps", test_mock_agent_max_steps),
]


def main():
    lines = ["Farzaan Dalwai - DATA 260 HW5"]
    passed = 0
    for name, test in TESTS:
        try:
            test()
        except Exception as exc:
            lines.append(f"FAIL: {name} ({exc})")
        else:
            lines.append(f"PASS: {name}")
            passed += 1
    lines.append(f"{passed}/{len(TESTS)} tests passed")
    text = "\n".join(lines)
    print(text)
    output = "reports/hw05/raw/part4_tests.txt"
    with open(output, "w") as file:
        file.write(text + "\n")
    if passed != len(TESTS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
