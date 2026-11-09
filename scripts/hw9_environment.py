import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from hw9_cache import redis_client


def output(*command):
    return subprocess.check_output(command, text=True).strip()


if __name__ == "__main__":
    repo = "repos/farzaandalwai/data260-0686"
    members = json.loads(output("gh", "api", repo + "/collaborators", "--jq", "[.[].login]"))
    data = {"timestamp": datetime.now(timezone.utc).isoformat(), "repository": "https://github.com/farzaandalwai/data260-0686",
            "hardware": output("sysctl", "-n", "machdep.cpu.brand_string"), "memory_bytes": int(output("sysctl", "-n", "hw.memsize")),
            "platform": platform.platform(), "python": platform.python_version(),
            "docker": output("docker", "version", "--format", "{{.Server.Version}}"),
            "redis": redis_client().info("server")["redis_version"],
            "models": [{"name": row["name"], "digest": row["digest"]} for row in requests.get("http://127.0.0.1:11434/api/tags", timeout=10).json()["models"] if row["name"] in ("llama3.2:latest", "nomic-embed-text:latest")],
            "required_accounts": [{"account": name, "permission": json.loads(output("gh", "api", repo + "/collaborators/" + name + "/permission"))["permission"], "listed_collaborator": name in members} for name in ("Sbnikitha", "supriyaselvanganesan")],
            "labels_commit": output("git", "log", "--diff-filter=A", "--format=%H", "--", "cache_cases.yaml"),
            "labels_committed_at": output("git", "show", "-s", "--format=%cI", "0cdc5328e78881f95f5756247ba0ee95c55162a6")}
    Path("reports/hw09/raw/environment.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))
