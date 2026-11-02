"""Collect unmodified console output and timestamped records for the report."""

from datetime import datetime, timezone
from pathlib import Path


def main():
    root = Path("reports/hw08")
    paths = sorted((root / "raw").glob("*.log")) + sorted((root / "raw").glob("events*.jsonl"))
    with (root / "RUN_LOG.txt").open("w") as output:
        output.write("HW8 actual console and event output\n")
        output.write("Collected at " + datetime.now(timezone.utc).isoformat() + "\n")
        output.write("Final reported experiment: raw/failure_results.json; earlier failed attempts are retained separately.\n")
        for path in paths:
            output.write("\nSOURCE: " + str(path) + "\n")
            output.write(path.read_text())
            output.write("\n")
    print(f"Collected {len(paths)} actual output files into {root / 'RUN_LOG.txt'}")


if __name__ == "__main__":
    main()
