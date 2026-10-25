import glob
import re
import shlex
import subprocess
from pathlib import Path


SAFE_PREFIXES = (("pwd",), ("ls",), ("rg",), ("find",), ("python3", "-m", "py_compile"))
SANDBOX_ROOT = None


def set_sandbox(path):
    global SANDBOX_ROOT
    SANDBOX_ROOT = Path(path).resolve()
    if not SANDBOX_ROOT.is_dir():
        raise ValueError("Sandbox directory does not exist")


def safe_path(path):
    if SANDBOX_ROOT is None:
        raise RuntimeError("Sandbox is not configured")
    candidate = (SANDBOX_ROOT / path).resolve()
    if not candidate.is_relative_to(SANDBOX_ROOT):
        raise ValueError("Path leaves course sandbox")
    return candidate


def read_file(path, max_lines=100):
    if not 1 <= max_lines <= 200:
        raise ValueError("max_lines must be 1 to 200")
    return "".join(safe_path(path).read_text().splitlines(keepends=True)[:max_lines])


def write_file(path, content):
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"path": str(target), "bytes": len(content.encode())}


def edit_file(path, diff):
    lines = diff.splitlines()
    if len(lines) != 2 or not lines[0].startswith("-") or not lines[1].startswith("+"):
        raise ValueError("Use a short -old/+new diff")
    target = safe_path(path)
    text = target.read_text()
    old, new = lines[0][1:], lines[1][1:]
    if not old or text.count(old) != 1:
        raise ValueError("Diff target must occur exactly once")
    target.write_text(text.replace(old, new, 1))
    return {"path": str(target), "changed": True, "diff": diff}


def glob_files(pattern):
    root = safe_path(".")
    return sorted(str(Path(name).relative_to(root)) for name in glob.glob(str(root / pattern), recursive=True) if Path(name).is_file() and Path(name).resolve().is_relative_to(root))


def search_in_files(query, file_pattern="*.py"):
    matches = []
    for path in glob_files(file_pattern):
        for line_number, line in enumerate(read_file(path, 200).splitlines(), 1):
            if query in line:
                matches.append({"file": path, "line": line_number, "text": line})
    return matches


def is_destructive(command):
    try:
        words = shlex.split(command)
    except ValueError:
        return True
    lowered = [word.lower() for word in words]
    if any(word in {"sudo", "chmod", "chown", "mkfs", "mkfs.ext4", "mkfs.apfs", "newfs", "diskutil"} or word.startswith("mkfs.") for word in lowered):
        return True
    if "rm" in lowered and any(word.startswith("-") and "r" in word for word in lowered[lowered.index("rm") + 1:]):
        return True
    if any(word.startswith("/dev/") for word in words):
        return True
    if "dd" in lowered and any(word.startswith("of=") for word in lowered):
        return True
    if "find" in lowered and any(word in {"-delete", "-exec", "-execdir", "-ok", "-okdir"} for word in lowered):
        return True
    if "rg" in lowered and any(word in {"--pre", "--pre-glob"} or word.startswith("--pre=") for word in lowered):
        return True
    if re.search(r">\s*(?:/|~)(?:\s|$|[^\s]*)", command):
        return True
    return False


def confirm_bash(command, auto_approve=False):
    if SANDBOX_ROOT is None:
        return {"allowed": False, "reason": "Sandbox is not configured"}
    try:
        words = shlex.split(command)
    except ValueError:
        return {"allowed": False, "reason": "Invalid shell quoting"}
    if is_destructive(command):
        return {"allowed": False, "reason": "Destructive command requires explicit confirmation"}
    if not any(tuple(words[:len(prefix)]) == prefix for prefix in SAFE_PREFIXES):
        return {"allowed": False, "reason": "Command prefix is not allowed"}
    if any(part in {";", "&&", "||", "|", ">", ">>", "<"} for part in words):
        return {"allowed": False, "reason": "Shell operators are not allowed"}
    if any(word.startswith("/") and not Path(word).resolve().is_relative_to(SANDBOX_ROOT) for word in words[1:]):
        return {"allowed": False, "reason": "Command path leaves sandbox"}
    if any(".." in Path(word).parts for word in words[1:]):
        return {"allowed": False, "reason": "Parent paths are not allowed"}
    return {"allowed": True, "reason": "Safe prefix and sandbox-local arguments"}


def bash(command, auto_approve=False):
    decision = confirm_bash(command, auto_approve)
    if not decision["allowed"]:
        return {**decision, "returncode": None, "output": ""}
    result = subprocess.run(shlex.split(command), cwd=SANDBOX_ROOT, capture_output=True, text=True, timeout=10)
    return {**decision, "returncode": result.returncode, "output": (result.stdout + result.stderr)[:4000]}
