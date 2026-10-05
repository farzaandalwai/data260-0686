import json
from datetime import datetime
from pathlib import Path

from hw5_tool_runtime import execute_tool
from src.model_client import complete


LOG_PATH = Path("reports/hw05/raw/agent_runs.jsonl")
SYSTEM_PROMPT = """
You help with rental housing listings. Reply with one JSON object and no other text.
The action field must be exactly "tool" or exactly "final".
Never put the tool name in the action field. Put the tool name in name.

To call a tool, copy this shape:
{"action": "tool", "name": "search_listings", "inputs": {"query": "San Jose", "limit": 5}}

name must be one of: search_listings, detail_lookup, aggregate_by_manager.
detail_lookup uses inputs {"listing_id": 1}.
aggregate_by_manager uses inputs {"manager_id": 1}.

To finish, copy this shape:
{"action": "final", "answer": "your answer"}

If a tool result says the listing is unavailable, finish and say it is unavailable.
A final answer may use only facts that appear in the tool results.
Do not invent an address, price, unit count, or any field the tool did not return.
Copy available_units exactly. If a field is missing, leave it out.
""".strip()


class MockModel:
    def __call__(self, messages):
        return json.dumps({
            "action": "tool",
            "name": "search_listings",
            "inputs": {"query": "San Jose", "limit": 5},
        })


def ollama_reply(messages):
    result = complete(messages, temperature=0.0, json_output=True)
    return result["message"]


TOOL_NAMES = ("search_listings", "detail_lookup", "aggregate_by_manager")


def tool_request(action):
    if not isinstance(action, dict):
        return None
    inputs = action.get("inputs") if isinstance(action.get("inputs"), dict) else {}
    if action.get("action") == "tool" and action.get("name") in TOOL_NAMES:
        return action["name"], inputs
    if action.get("action") in TOOL_NAMES:
        return action["action"], inputs
    return None


def parse_action(text):
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        action = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(action, dict):
        return None
    return action


def append_run(record):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as file:
        file.write(json.dumps(record) + "\n")


def run_agent(user_input, model=None, max_steps=4, execute=None, scenario="agent"):
    reply = model or ollama_reply
    call_tool = execute or execute_tool
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    steps = []
    stop_reason = "max_steps"
    final_answer = None
    for step_number in range(1, max_steps + 1):
        try:
            raw = reply(messages)
        except Exception:
            steps.append({"step": step_number, "model_action": None, "error": "model request failed"})
            stop_reason = "model_error"
            break
        action = parse_action(raw)
        step = {"step": step_number, "model_action": action if action is not None else raw}
        if not action:
            steps.append(step)
            stop_reason = "model_error"
            break
        if action.get("action") == "final":
            final_answer = action.get("answer")
            steps.append(step)
            stop_reason = "normal_completion"
            break
        request = tool_request(action)
        if request is None:
            steps.append(step)
            stop_reason = "model_error"
            break
        name, inputs = request
        result = call_tool(name, inputs)
        step["tool_name"] = name
        step["tool_inputs"] = inputs
        step["tool_result"] = result
        steps.append(step)
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Tool result: " + result})
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = {}
        if parsed.get("error") == "Listing is unavailable":
            stop_reason = "safety_block"
            break
    tool_calls = sum(1 for step in steps if step.get("tool_name"))
    record = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scenario": scenario,
        "user_input": user_input,
        "max_steps": max_steps,
        "steps": steps,
        "tool_calls": tool_calls,
        "final_answer": final_answer,
        "stop_reason": stop_reason,
    }
    append_run(record)
    return record
