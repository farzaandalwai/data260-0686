import json
import urllib.request

MODEL = "llama3.2:latest"
URL = "http://localhost:11434/api/chat"


def complete(messages, tools=None, temperature=None, json_output=False):
    data = {
        "model": MODEL,
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

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())

    return {
        "message": result["message"]["content"],
        "input_tokens": result.get("prompt_eval_count", 0),
        "output_tokens": result.get("eval_count", 0)
    }