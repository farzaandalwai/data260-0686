import json
import re
from pathlib import Path

from hw7_agent import run_agent


TASKS = {
    "A": "Find a San Jose rental listing. Search, inspect one returned listing, and report its property title, available units, and manager name.",
    "B": "For property manager ID 1, report the total listing count and available units. Then find and inspect one of that manager's listings as a supporting example, naming its title.",
    "C": "Compare two different San Jose rental listings. Search first, inspect details for two returned IDs, then name both property titles and compare their available units.",
}


def verify(record):
    successes = [step for step in record["trace"] if step.get("tool") and step["observation"].get("ok")]
    details = [step["observation"]["data"] for step in successes if step["tool"] == "detail_lookup"]
    answer = (record["answer"] or "").lower()
    reasons = []
    unsupported = False
    if record["stop_reason"] != "success":
        reasons.append(record["stop_reason"])
    if record["task"] == "A":
        if re.search(r"\bthere (?:are|is) \d+ rental listings\b", answer) and not any(step["tool"] == "aggregate_by_manager" for step in successes):
            reasons.append("limited search count stated as a total; say these are examples")
            unsupported = True
        if not details:
            reasons.append("missing listing detail")
        elif not all(str(value).lower() in answer for value in (
            details[0]["property_title"], details[0]["available_units"], details[0]["manager"]["first_name"]
        )):
            reasons.append("answer omits title, units, or manager evidence")
    elif record["task"] == "B":
        aggregates = [step["observation"]["data"] for step in successes if step["tool"] == "aggregate_by_manager"]
        if not aggregates or not details:
            reasons.append("missing aggregate or supporting detail")
        elif str(aggregates[0]["listing_count"]) not in answer or details[0]["property_title"].lower() not in answer:
            reasons.append("answer omits count or example title")
    else:
        if len({detail["id"] for detail in details}) < 2:
            reasons.append("missing second distinct detail")
        elif any(detail["property_title"].lower() not in answer for detail in details[:2]):
            reasons.append("answer omits one compared title")
    return {"passed": not reasons, "reasons": reasons, "unsupported_claim": unsupported}


def reflect(record, verdict):
    calls = [step["tool"] for step in record["trace"] if step.get("tool")]
    evidence = ", ".join(calls) or "none"
    return f"Your last attempt used {evidence}. It failed because: {'; '.join(verdict['reasons'])}. Use the missing tools, then include the exact facts from their observations."


def run_reflexion(task, first_step_budget=7):
    attempts = []
    feedback = None
    used_tools = 0
    used_tokens = 0
    for retry in range(3):
        if used_tools >= 12 or used_tokens >= 12000:
            return {"task": task, "attempts": attempts, "stop_reason": "budget_exhausted"}
        record = run_agent(
            TASKS[task], task=task, reflection=feedback,
            max_steps=first_step_budget if retry == 0 else 7,
            max_tools=min(5, 12 - used_tools), max_tokens=12000 - used_tokens,
        )
        used_tools += record["tool_calls"]
        used_tokens += record["input_tokens"] + record["output_tokens"]
        verdict = verify(record)
        attempts.append({"run": record, "verdict": verdict})
        if verdict["passed"]:
            return {"task": task, "attempts": attempts, "stop_reason": "success"}
        if used_tools >= 12 or used_tokens >= 12000:
            return {"task": task, "attempts": attempts, "stop_reason": "budget_exhausted"}
        feedback = reflect(record, verdict)
    return {"task": task, "attempts": attempts, "stop_reason": "human_review"}


def run_experiments():
    target = Path("reports/hw07/raw")
    target.mkdir(parents=True, exist_ok=True)
    baseline = []
    sequence = ["A", "B", "C"] * 7
    for index, task in enumerate(sequence[:20], 1):
        record = run_agent(TASKS[task], task=task)
        item = {"attempt": index, "run": record, "verdict": verify(record)}
        baseline.append(item)
        print(f"baseline {index:02d} {task} calls={record['tool_calls']} stop={record['stop_reason']} verified={item['verdict']['passed']}", flush=True)
    (target / "part2_attempts.json").write_text(json.dumps(baseline, indent=2))
    reflexion = []
    for task in TASKS:
        item = run_reflexion(task)
        reflexion.append(item)
        print(f"reflexion {task} attempts={len(item['attempts'])} stop={item['stop_reason']}", flush=True)
    (target / "part3_reflexion.json").write_text(json.dumps(reflexion, indent=2))


if __name__ == "__main__":
    run_experiments()
