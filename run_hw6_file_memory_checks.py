"""Objectively verify the HW6 file-memory system and command behavior."""

import json

from hw6_config import ROOT
from hw6_file_memory import (
    MEMORY_PATH,
    command_help,
    contradiction_validation,
    count_memory_lines,
    handle_file_command,
    verify_agent_compliance,
)


def main() -> None:
    raw = ROOT / "reports" / "hw06" / "raw"
    original = (raw / "memory_original_55.md").read_text(encoding="utf-8")
    consolidated = (raw / "memory_consolidated.md").read_text(encoding="utf-8")
    root_before_dream = MEMORY_PATH.read_text(encoding="utf-8")
    dream = handle_file_command(
        "/dream",
        [{"role": "user", "content": "I prefer a rental with secure bicycle storage."}],
    )
    dream_count = count_memory_lines()
    MEMORY_PATH.write_text(root_before_dream, encoding="utf-8")
    help_result = handle_file_command("/help", [])
    memory_result = handle_file_command("/memory", [])
    contradiction = contradiction_validation(consolidated)
    agent = verify_agent_compliance()
    checks = {
        "original_has_exactly_55_fact_lines": count_memory_lines(original) == 55,
        "consolidated_has_fewer_than_40_fact_lines": count_memory_lines(consolidated) < 40,
        "root_is_consolidated_version": MEMORY_PATH.read_text(encoding="utf-8") == consolidated,
        "contradiction_outcomes_pass": contradiction["all_pass"],
        "dream_appended_one_known_file_fact": dream["added"] == 1 and dream_count == count_memory_lines(consolidated) + 1,
        "help_lists_all_exact_commands": all(
            command in help_result["text"] for command in ("/memory", "/compact", "/dream", "/help")
        ),
        "memory_command_returns_current_file": memory_result["count"] == count_memory_lines(consolidated),
        "agent_compliance_pass": agent["pass"],
    }
    payload = {
        "checks": checks,
        "all_pass": all(checks.values()),
        "counts": {
            "original": count_memory_lines(original),
            "consolidated": count_memory_lines(consolidated),
        },
        "contradiction_validation": contradiction,
        "dream_result": dream,
        "agent_compliance": agent,
        "command_help": command_help(),
    }
    (raw / "file_memory_checks.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (raw / "contradiction_validation.json").write_text(
        json.dumps(contradiction, indent=2) + "\n", encoding="utf-8"
    )
    (raw / "agent_compliance.json").write_text(
        json.dumps(agent, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))
    if not payload["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
