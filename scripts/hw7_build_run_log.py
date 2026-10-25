import json
from pathlib import Path


ROOT = Path("reports/hw07")
RAW = ROOT / "raw"


def load(name):
    return json.loads((RAW / name).read_text())


def main():
    lines = ["DATA 260 HW7 run log", "Times below are real UTC timestamps stored by the run scripts.", ""]
    for item in load("part2_attempts.json"):
        run = item["run"]
        lines.append(f"{run['timestamp']} baseline {item['attempt']:02d} task={run['task']} calls={run['tool_calls']} stop={run['stop_reason']} verified={item['verdict']['passed']} reasons={item['verdict']['reasons']}")
    lines.append("")
    for item in load("part3_reflexion.json"):
        for number, attempt in enumerate(item["attempts"], 1):
            run = attempt["run"]
            lines.append(f"{run['timestamp']} reflexion task={item['task']} attempt={number} calls={run['tool_calls']} stop={run['stop_reason']} verified={attempt['verdict']['passed']} reasons={attempt['verdict']['reasons']}")
    probe = load("part3_failed_retry_probe.json")
    for number, attempt in enumerate(probe["attempts"], 1):
        run = attempt["run"]
        lines.append(f"{run['timestamp']} tight-step probe attempt={number} calls={run['tool_calls']} stop={run['stop_reason']} verified={attempt['verdict']['passed']}")
    lines.append("")
    for scenario in ("member", "sparse"):
        item = load(f"bike_{scenario}_trace.json")
        result = item["result"]
        lines.append(f"{item['timeline'][0]['observation']['ts']} bike {scenario} rows={result['total_csv_rows']} selected={result['scenario_rides']} calls={item['tool_calls']} stop={item['stop_reason']} decision={result['decision']}")
        for event in item["timeline"]:
            lines.append(f"{event['observation']['ts']}   {event['tool']} success={event['observation']['success']}")
    lines.append("")
    for item in load("part5_injection_traces.json"):
        lines.append(f"{item['timestamp']} injection attack={item['attack']} defense={item['defense']} wrong={item['wrong_decision']} non_select_attempt={item['attempted_non_select']} contaminated={item['contaminated']}")
    sandbox = load("part6_sandbox.json")
    lines.append("")
    lines.append(f"{sandbox['timestamp']} sandbox debug_matches={len(sandbox['discovery']['search'])} allowed={sum(x['result']['allowed'] for x in sandbox['allowed'])}/5 blocked={sum(not x['result']['allowed'] for x in sandbox['blocked'])}/5 passed={sandbox['passed']}")
    verification = json.loads((ROOT / "verification.json").read_text())
    lines.append(f"{verification['timestamp_utc']} live verification passed={verification['passed']}/{len(verification['checks'])}")
    (ROOT / "RUN_LOG.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
