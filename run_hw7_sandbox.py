import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from hw7_file_tools import bash, confirm_bash, edit_file, glob_files, read_file, search_in_files, set_sandbox, write_file


ALLOWED = ["pwd", "ls", "ls alpha.py", "find . -name '*.py'", "python3 -m py_compile alpha.py"]
BLOCKED = ["rm -rf .", "sudo ls", "chmod 777 alpha.py", "dd if=alpha.py of=/dev/disk0", "echo hi > /etc/passwd"]


def main():
    with tempfile.TemporaryDirectory(prefix="s0686_hw7_sandbox_") as folder:
        set_sandbox(folder)
        write_file("alpha.py", "DEBUG = True\nVALUE = 1\n")
        write_file("beta.py", "def check():\n    return 'DEBUG here'\n")
        write_file("gamma.py", "VALUE = 3\n")
        discovery = {"glob": glob_files("*.py"), "search": search_in_files("DEBUG", "*.py"), "read": read_file("alpha.py", max_lines=2)}
        edit_file("gamma.py", "-VALUE = 3\n+VALUE = 4")
        allowed = [{"command": command, "result": bash(command, auto_approve=True)} for command in ALLOWED]
        blocked = [{"command": command, "result": confirm_bash(command, auto_approve=True)} for command in BLOCKED]
        passed = len(discovery["glob"]) == 3 and len(discovery["search"]) == 2
        passed = passed and all(item["result"]["allowed"] for item in allowed)
        passed = passed and all(not item["result"]["allowed"] for item in blocked)
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "discovery": discovery, "allowed": allowed, "blocked": blocked, "passed": passed}
        target = Path("reports/hw07/raw/part6_sandbox.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, indent=2))
        print(f"Sandbox: 3 Python files; glob -> search -> read found {len(discovery['search'])} DEBUG matches")
        print(f"glob: {discovery['glob']}")
        for match in discovery["search"]:
            print(f"search: {match['file']}:{match['line']} {match['text']}")
        print(f"read alpha.py: {discovery['read'].strip()!r}")
        for number, item in enumerate(allowed, 1):
            print(f"ALLOW {number}: {item['command']} -> rc={item['result']['returncode']}")
        for number, item in enumerate(blocked, 1):
            print(f"BLOCK {number}: {item['command']} -> {item['result']['reason']}")
        print(f"Gate: {sum(item['result']['allowed'] for item in allowed)}/5 allowed; {sum(not item['result']['allowed'] for item in blocked)}/5 blocked")
        print("PASS" if passed else "FAIL")
        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
