import json
from pathlib import Path

from hw7_bike_agent import analyze_bike


RAW = Path("reports/hw07/raw")


def main():
    for name in ("member", "sparse"):
        csv_text = (RAW / f"divvy_{name}.csv").read_text()
        result = analyze_bike(csv_text)
        (RAW / f"bike_{name}_trace.json").write_text(json.dumps(result, indent=2))
        summary = result.get("result") or {}
        print(f"{name}: rows={summary.get('total_csv_rows')} rides={summary.get('scenario_rides')} calls={result['tool_calls']} decision={summary.get('decision')} stop={result['stop_reason']}")


if __name__ == "__main__":
    main()
