import json


def default_tools():
    from mcp_servers.rentals_server import aggregate_by_manager
    from mcp_servers.rentals_server import detail_lookup
    from mcp_servers.rentals_server import search_listings

    return {
        "search_listings": search_listings,
        "detail_lookup": detail_lookup,
        "aggregate_by_manager": aggregate_by_manager,
    }


def envelope(data=None, error=None):
    return {"ok": error is None, "data": data, "error": error}


def normalize_inputs(name, inputs):
    cleaned = dict(inputs or {})
    if name == "search_listings" and "limit" in cleaned:
        cleaned["limit"] = int(cleaned["limit"])
    if name == "detail_lookup" and "listing_id" in cleaned:
        cleaned["listing_id"] = int(cleaned["listing_id"])
    if name == "aggregate_by_manager" and "manager_id" in cleaned:
        cleaned["manager_id"] = int(cleaned["manager_id"])
    return cleaned


def apply_safety(name, result):
    if name != "detail_lookup" or not result.get("ok"):
        return result
    data = result.get("data") or {}
    units = data.get("available_units")
    if units is not None and units <= 0:
        return envelope(error="Listing is unavailable")
    return result


def execute_tool(name, inputs, tools=None):
    selected = tools if tools is not None else default_tools()
    if name not in selected:
        return json.dumps(envelope(error="Unknown tool."))
    try:
        result = selected[name](**normalize_inputs(name, inputs))
    except (TypeError, ValueError):
        return json.dumps(envelope(error="Invalid tool inputs."))
    except Exception:
        return json.dumps(envelope(error="Tool call failed."))
    if not isinstance(result, dict):
        return json.dumps(envelope(error="Tool returned an unexpected result."))
    return json.dumps(apply_safety(name, result))
