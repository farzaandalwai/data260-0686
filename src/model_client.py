import json
import os
import time
import urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")


def complete(messages, tools=None, temperature=None, json_output=False, model=None):
    data = {
        "model": model or MODEL,
        "messages": messages,
        "stream": False
    }

    if tools:
        data["tools"] = tools

    if temperature is not None:
        data["options"] = {"temperature": temperature}

    if json_output:
        data["format"] = "json"

    req = urllib.request.Request(
        URL,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )

    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode())
    latency_ms = round((time.perf_counter() - started) * 1000, 3)

    return {
        "message": result["message"]["content"],
        "input_tokens": result.get("prompt_eval_count", 0),
        "output_tokens": result.get("eval_count", 0),
        "latency_ms": latency_ms,
        "model": result.get("model", model or MODEL),
    }
