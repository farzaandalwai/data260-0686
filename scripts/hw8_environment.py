import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def output(*command):
    return subprocess.check_output(command, text=True).strip()


def main():
    repo = "repos/farzaandalwai/data260-0686"
    data = {"captured_utc": datetime.now(timezone.utc).isoformat(), "repository": json.loads(output("gh", "api", repo, "--jq", "{html_url,private,default_branch}")),
            "collaborators": [json.loads(output("gh", "api", repo + "/collaborators/" + name + "/permission", "--jq", "{user:.user.login,permission}")) for name in ("Sbnikitha", "supriyaselvanganesan")],
            "hardware": output("sysctl", "-n", "machdep.cpu.brand_string"), "memory_bytes": int(output("sysctl", "-n", "hw.memsize")),
            "platform": platform.platform(), "python": platform.python_version(),
            "docker": output("docker", "version", "--format", "{{.Server.Version}}"),
            "image": output("docker", "image", "inspect", "apache/kafka:4.1.2", "--format", "{{json .RepoDigests}}"),
            "containers": output("docker", "compose", "-f", "compose.hw08.yml", "ps", "--format", "json")}
    Path("reports/hw08/raw/environment.json").write_text(json.dumps(data, indent=2))
    print(json.dumps({key: value for key, value in data.items() if key != "containers"}, indent=2))


if __name__ == "__main__":
    main()
