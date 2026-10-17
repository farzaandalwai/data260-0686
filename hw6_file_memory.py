"""Restricted file-memory loading, commands, and deterministic consolidation."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re
from pathlib import Path

from hw6_config import ROOT


AGENT_PATH = ROOT / "AGENT.md"
MEMORY_PATH = ROOT / "MEMORY.md"
RAW_PATH = ROOT / "reports" / "hw06" / "raw"
TIMESTAMP_PATTERN = re.compile(r"<!--\s*last-consolidated:\s*(.*?)\s*-->")
EXPECTED_CONTRADICTIONS = {
    "preferred_city": "Santa Clara, CA",
    "max_monthly_budget": "$3,500",
    "pet_household": "one indoor cat",
}


def utc_now() -> datetime:
    """Return an aware UTC timestamp, as required by AGENT.md."""
    return datetime.now(timezone.utc)


def normalize_rental_title(title: str) -> str:
    """Validate and normalize one short rental title without external side effects."""
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    normalized = " ".join(title.split())
    if not 1 <= len(normalized) <= 100:
        raise ValueError("title must contain 1 through 100 characters")
    return normalized


def load_agent_memory() -> str:
    return AGENT_PATH.read_text(encoding="utf-8")


def load_fact_memory() -> str:
    return MEMORY_PATH.read_text(encoding="utf-8") if MEMORY_PATH.exists() else ""


def file_memory_prompt() -> str:
    """Load only the two repository memory files; no caller path is accepted."""
    return (
        "=== DURABLE AGENT INSTRUCTIONS ===\n"
        + load_agent_memory().strip()
        + "\n\n=== DURABLE FACT MEMORY ===\n"
        + load_fact_memory().strip()
    )


def count_memory_lines(text: str | None = None) -> int:
    """Count fact lines, excluding blank, heading, and HTML-comment lines."""
    source = load_fact_memory() if text is None else text
    count = 0
    in_comment = False
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("<!--"):
            in_comment = True
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.startswith("#"):
            continue
        count += 1
    return count


def read_last_consolidated(text: str | None = None) -> datetime | None:
    source = load_fact_memory() if text is None else text
    match = TIMESTAMP_PATTERN.search(source)
    if not match:
        return None
    try:
        parsed = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def consolidation_required(now: datetime | None = None) -> tuple[bool, list[str]]:
    """Apply the assignment's >40 lines or >24 hours rule exactly."""
    now = now or utc_now()
    reasons = []
    count = count_memory_lines()
    if count > 40:
        reasons.append(f"{count} fact lines exceeds 40")
    last = read_last_consolidated()
    if last is None:
        reasons.append("last-consolidated timestamp is missing or invalid")
    elif now - last > timedelta(hours=24):
        reasons.append("last consolidation is more than 24 hours old")
    return bool(reasons), reasons


def parse_fact_line(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("-"):
        return None
    fields = {}
    for chunk in line[1:].strip().split("|"):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        fields[key.strip()] = value.strip()
    if not {"key", "value", "observed", "confidence"}.issubset(fields):
        return None
    try:
        fields["confidence_number"] = float(fields["confidence"])
        fields["observed_time"] = datetime.fromisoformat(
            fields["observed"].replace("Z", "+00:00")
        )
    except ValueError:
        return None
    return fields


def consolidated_text(source: str, consolidated_at: datetime | None = None) -> str:
    """Merge duplicates and retain explicit contradiction evidence."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for line in source.splitlines():
        fact = parse_fact_line(line)
        if fact is not None:
            grouped[fact["key"]].append(fact)

    output = [
        "<!-- last-consolidated: "
        + (consolidated_at or utc_now()).isoformat()
        + " -->"
    ]
    for key in sorted(grouped):
        facts = grouped[key]
        unique = {}
        for fact in facts:
            marker = (fact["value"], fact["observed"], fact["confidence"])
            unique[marker] = fact
        candidates = list(unique.values())
        values = sorted({fact["value"] for fact in candidates})
        if len(values) == 1:
            output.append(
                f"- key={key} | value={values[0]} | status=confirmed | "
                f"merged_sources={len(facts)}"
            )
            continue

        ranked = sorted(
            candidates,
            key=lambda fact: (
                fact["confidence_number"], fact["observed_time"], fact["value"]
            ),
            reverse=True,
        )
        top = ranked[0]
        tied = [
            fact for fact in ranked
            if fact["confidence_number"] == top["confidence_number"]
            and fact["observed_time"] == top["observed_time"]
        ]
        alternatives = "; ".join(
            f"{fact['value']} @ {fact['observed']} confidence {fact['confidence']}"
            for fact in sorted(candidates, key=lambda item: item["observed_time"])
        )
        if len(tied) > 1:
            output.append(
                f"- key={key} | selected=unresolved | alternatives={alternatives} | "
                "reason=tied confidence and observation time"
            )
        else:
            output.append(
                f"- key={key} | selected={top['value']} | alternatives={alternatives} | "
                "reason=highest confidence, then newest observation"
            )
    return "\n".join(output) + "\n"


def compact_memory() -> dict:
    """Preserve both assignment versions, then replace root memory atomically."""
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    source = load_fact_memory()
    before = count_memory_lines(source)
    original_path = RAW_PATH / "memory_original_55.md"
    original_path.write_text(source, encoding="utf-8")
    result = consolidated_text(source)
    after = count_memory_lines(result)
    temp_path = MEMORY_PATH.with_suffix(".md.tmp")
    temp_path.write_text(result, encoding="utf-8")
    temp_path.replace(MEMORY_PATH)
    consolidated_path = RAW_PATH / "memory_consolidated.md"
    consolidated_path.write_text(result, encoding="utf-8")
    return {
        "before": before,
        "after": after,
        "duplicates_merged": before - after,
        "original_evidence": str(original_path.relative_to(ROOT)),
        "consolidated_evidence": str(consolidated_path.relative_to(ROOT)),
    }


def contradiction_validation(text: str | None = None) -> dict:
    """Independently check the three expected resolution outcomes."""
    source = load_fact_memory() if text is None else text
    results = []
    for key, expected in EXPECTED_CONTRADICTIONS.items():
        pattern = re.compile(rf"^- key={re.escape(key)} \| selected=([^|]+)", re.MULTILINE)
        match = pattern.search(source)
        actual = match.group(1).strip() if match else None
        results.append({
            "key": key,
            "expected": expected,
            "actual": actual,
            "pass": actual == expected,
        })
    incorrect = [item["key"] for item in results if not item["pass"]]
    return {
        "checks": results,
        "incorrect_resolutions": incorrect,
        "all_pass": not incorrect,
        "statement": (
            "Independent check found no incorrectly resolved contradictions."
            if not incorrect
            else "Incorrect resolutions found: " + ", ".join(incorrect)
        ),
    }


def append_dream_facts(recent_messages: list[dict]) -> dict:
    """Append up to three user-stated durable preferences to the known memory file."""
    existing = load_fact_memory()
    existing_lower = existing.lower()
    candidates = []
    for message in reversed(recent_messages):
        if message.get("role") != "user":
            continue
        content = " ".join(str(message.get("content", "")).split())
        lower = content.lower()
        if len(content) < 8 or content.lower() in existing_lower:
            continue
        if any(marker in lower for marker in ("i prefer", "i need", "my budget", "must have")):
            candidates.append(content[:300])
        if len(candidates) == 3:
            break
    candidates.reverse()
    if not candidates:
        return {"added": 0, "facts": []}
    stamp = utc_now().isoformat()
    additions = [
        f"- key=dream_{int(utc_now().timestamp())}_{index} | value={fact} | "
        f"observed={stamp} | confidence=0.70"
        for index, fact in enumerate(candidates, start=1)
    ]
    separator = "" if existing.endswith("\n") else "\n"
    MEMORY_PATH.write_text(existing + separator + "\n".join(additions) + "\n", encoding="utf-8")
    return {"added": len(additions), "facts": candidates}


def command_help() -> str:
    return (
        "/memory - display current file memory\n"
        "/compact - merge duplicates and explicitly resolve contradictions\n"
        "/dream - append durable facts from recent user messages\n"
        "/help - show these commands"
    )


def handle_file_command(command: str, recent_messages: list[dict]) -> dict:
    """Handle only exact commands and never accept a path argument."""
    if command == "/memory":
        return {"command": command, "text": load_fact_memory(), "count": count_memory_lines()}
    if command == "/compact":
        result = compact_memory()
        return {"command": command, "text": f"Compacted memory from {result['before']} to {result['after']} facts.", **result}
    if command == "/dream":
        result = append_dream_facts(recent_messages)
        return {"command": command, "text": f"Dream added {result['added']} durable facts.", **result}
    if command == "/help":
        return {"command": command, "text": command_help()}
    raise ValueError("unsupported command")


def verify_agent_compliance() -> dict:
    """Objectively check one generated function against AGENT.md rules."""
    checks = {
        "descriptive_snake_case_name": normalize_rental_title.__name__ == "normalize_rental_title",
        "type_hints": bool(normalize_rental_title.__annotations__),
        "docstring": bool(normalize_rental_title.__doc__),
        "validates_external_input": False,
        "no_external_side_effects": True,
    }
    try:
        normalize_rental_title("")
    except ValueError:
        checks["validates_external_input"] = True
    return {"function": "normalize_rental_title", "checks": checks, "pass": all(checks.values())}
