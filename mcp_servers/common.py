def response(data=None, error=None) -> dict:
    return {"ok": error is None, "data": data, "error": error}
