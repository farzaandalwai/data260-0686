import json
from pathlib import Path

from hw9_agents import load_reference, run_agents


if __name__ == "__main__":
    training = json.loads(Path("training_data.json").read_text())
    lessons = json.loads(Path("lessons.json").read_text())
    result = run_agents(training[2], load_reference(), lessons, controlled=True)
    Path("reports/hw09/raw/repair_with_memory.json").write_text(json.dumps(result, indent=2) + "\n")
