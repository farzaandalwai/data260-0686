import json
import time
from datetime import datetime, timezone

from hw5_tool_runtime import execute_tool
from src.model_client import complete


TOOL_FIELDS = {
    "search_listings": {"query": str, "limit": int},
    "detail_lookup": {"listing_id": int},
    "aggregate_by_manager": {"manager_id": int},
}
SYSTEM = """You are a rental-housing tool agent. Return exactly one JSON object per turn.
To use a tool: {"action":"tool","name":"search_listings","inputs":{"query":"San Jose","limit":3}}.
Other tools: detail_lookup with integer listing_id; aggregate_by_manager with integer manager_id.
To finish: {"action":"final","answer":"brief factual answer"}.
Use tool observations as evidence. Never invent a listing, count, address, price or manager.
For a search result, call detail_lookup on a returned ID before answering.
For a manager count, call aggregate_by_manager and then find and detail a supporting listing.
For a comparison, search first, then detail two distinct returned IDs before answering.
If a listing ID is absent, say it was not found."""


def validate_action(raw):
    try:
        action = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, "malformed_arguments"
    if not isinstance(action, dict):
        return None, "malformed_arguments"
    if action.get("action") == "final":
        if isinstance(action.get("answer"), str):
            return action, None
        return None, "malformed_arguments"
    if action.get("action") in TOOL_FIELDS and "name" not in action:
        action["name"] = action["action"]
        action["action"] = "tool"
    if action.get("action") != "tool":
        return None, "text_when_tool_required"
    name = action.get("name")
    if name not in TOOL_FIELDS:
        return None, "unknown_tool"
    inputs = action.get("inputs")
    if not isinstance(inputs, dict):
        return None, "malformed_arguments"
    required = TOOL_FIELDS[name]
    if any(key not in inputs or type(inputs[key]) is not kind for key, kind in required.items() if key != "limit"):
        return None, "schema_failure"
    if name == "search_listings" and ("limit" in inputs and type(inputs["limit"]) is not int):
        return None, "schema_failure"
    if any(key not in required for key in inputs):
        return None, "schema_failure"
    return action, None


def repair_prompt(error):
    return {
        "malformed_arguments": "Your last JSON was malformed. Return one valid JSON object with action, name, and inputs; no surrounding prose.",
        "unknown_tool": "Unknown tool. Choose only search_listings, detail_lookup, or aggregate_by_manager with the documented inputs.",
        "schema_failure": "Tool inputs do not match the schema. search_listings needs string query; detail_lookup needs integer listing_id; aggregate_by_manager needs integer manager_id.",
        "text_when_tool_required": "A tool call is required before your final answer. Return a JSON tool action now.",
    }[error]


def evidence_check(task, trace, answer):
    calls = [step for step in trace if step.get("tool")]
    names = [step["tool"] for step in calls]
    if task == "N":
        missing = any(step["tool"] == "detail_lookup" and "not found" in (step["observation"].get("error") or "").lower() for step in calls)
        return missing and any(phrase in answer.lower() for phrase in ("not found", "unavailable", "does not exist", "doesn't exist"))
    if task == "A":
        good = "search_listings" in names and "detail_lookup" in names and names.index("search_listings") < names.index("detail_lookup")
    elif task == "B":
        good = "aggregate_by_manager" in names and "detail_lookup" in names
    else:
        ids = [step["inputs"]["listing_id"] for step in calls if step["tool"] == "detail_lookup"]
        good = "search_listings" in names and len(set(ids)) >= 2
    return good


def run_agent(user_input, task="A", reflection=None, max_steps=7, max_tools=5, max_tokens=5000):
    started = time.perf_counter()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_input}]
    if reflection:
        messages.append({"role": "user", "content": f"Verifier feedback for this run only: {reflection}"})
    trace = []
    totals = {"input_tokens": 0, "output_tokens": 0, "tool_calls": 0}
    repair_used = False
    answer = None
    stop = "budget_exhausted"
    for number in range(1, max_steps + 1):
        if totals["input_tokens"] + totals["output_tokens"] >= max_tokens:
            break
        try:
            result = complete(messages, temperature=0.0, json_output=True, model="llama3.2:latest", num_predict=min(240, max_tokens - totals["input_tokens"] - totals["output_tokens"]))
        except Exception as error:
            trace.append({"step": number, "failure": "model_error", "detail": type(error).__name__})
            stop = "human_review"
            break
        totals["input_tokens"] += result["input_tokens"]
        totals["output_tokens"] += result["output_tokens"]
        if totals["input_tokens"] + totals["output_tokens"] > max_tokens:
            trace.append({"step": number, "failure": "token_budget"})
            break
        raw = result["message"]
        action, failure = validate_action(raw)
        step = {"step": number, "model_output": raw, "failure": failure}
        if failure:
            trace.append(step)
            if repair_used:
                stop = "human_review"
                break
            repair_used = True
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": repair_prompt(failure)})
            continue
        if action["action"] == "final":
            answer = action["answer"]
            if evidence_check(task, trace, answer):
                stop = "success"
            else:
                step["failure"] = "lost_chain"
                stop = "human_review"
            trace.append(step)
            break
        if totals["tool_calls"] >= max_tools:
            step["failure"] = "tool_budget"
            trace.append(step)
            break
        name, inputs = action["name"], action["inputs"]
        observation = execute_tool(name, inputs)
        step.update({"tool": name, "inputs": inputs, "observation": json.loads(observation)})
        trace.append(step)
        totals["tool_calls"] += 1
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "tool", "content": observation})
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "prompt": user_input,
        "reflection": reflection,
        "answer": answer,
        "stop_reason": stop,
        "repair_used": repair_used,
        "trace": trace,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        **totals,
    }
