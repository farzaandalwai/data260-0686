import json
import sys
from pathlib import Path


RAW = Path("reports/hw07/raw")


def load(name):
    return json.loads((RAW / name).read_text())


def agent():
    records = load("part2_attempts.json")
    for task in ("A", "B", "C"):
        item = next(item for item in records if item["run"]["task"] == task)
        run = item["run"]
        print(f"Task {task}: {run['stop_reason']}; {run['tool_calls']} real tool calls; verifier={item['verdict']['passed']}")
        for step in run["trace"]:
            if step.get("tool"):
                print(f"  {step['tool']} {step['inputs']}")
        print(f"  final: {run['answer']}")
    missing = load("part2_nonexistent_id.json")
    print(f"Missing ID: {missing['stop_reason']}; {missing['answer']}")


def reliability():
    records = load("part2_attempts.json")
    calls = sum(item["run"]["tool_calls"] for item in records)
    repaired = sum(item["run"]["repair_used"] for item in records)
    failures = {name: sum(step.get("failure") == name for item in records for step in item["run"]["trace"]) for name in ("malformed_arguments", "unknown_tool", "text_when_tool_required", "schema_failure", "lost_chain")}
    print(f"20 trials: {sum(item['verdict']['passed'] for item in records)}/20 verified; {calls} tool calls")
    print(f"Well-formed before repair: {calls}/{calls} (100%); after repair: {calls}/{calls} (100%); repairs used: {repaired}")
    print(f"Failure categories: {failures}")


def reflexion():
    records = load("part3_reflexion.json")
    for item in records:
        print(f"Task {item['task']}: {item['stop_reason']}; attempts={len(item['attempts'])}")
        for number, attempt in enumerate(item["attempts"], 1):
            run = attempt["run"]
            print(f"  attempt {number}: calls={run['tool_calls']}, verified={attempt['verdict']['passed']}, reasons={attempt['verdict']['reasons']}")
            if run["reflection"]:
                print(f"  reflection: {run['reflection']}")
    probe = load("part3_failed_retry_probe.json")
    for number, attempt in enumerate(probe["attempts"], 1):
        run = attempt["run"]
        print(f"Probe attempt {number}: {run['stop_reason']}; calls={run['tool_calls']}; verifier={attempt['verdict']['reasons']}")
        if run["reflection"]:
            print(f"  reflection: {run['reflection']}")
    print(f"Probe final: {probe['stop_reason']}")


def injection():
    for item in load("part5_injection_traces.json"):
        blocked = item.get("fixture_gate_probe")
        print(f"{item['defense']} / {item['attack']}: wrong={item['wrong_decision']}, SQL_attempt={item['attempted_non_select']}, contaminated={item['contaminated']}, SQL_gate_blocked={blocked is not None and not blocked['success']}")
        if item.get("correction"):
            print(f"  {item['correction']}")


if __name__ == "__main__":
    {"agent": agent, "reliability": reliability, "reflexion": reflexion, "injection": injection}[sys.argv[1]]()
