import copy
import hashlib
import json
from pathlib import Path

from hw9_agents import lesson, load_reference, run_agents, validate_lesson
from hw9_cache import RAW, log


def save(name, data):
    (RAW / name).write_text(json.dumps(data, indent=2) + "\n")


def main():
    reference = load_reference()
    training = json.loads(Path("training_data.json").read_text())
    validation = json.loads(Path("validation_data.json").read_text())
    controlled = [run_agents(item, reference, [], controlled=True) for item in training[:2]]
    assert all(row["attempts"][0]["evaluation"]["result"] == "REVISE" for row in controlled)
    save("repair_demo.json", controlled)
    lessons = [lesson("lesson_001", "Repeated omission of available_units",
                      "When available_units is requested, include its current reference value, including zero; do not omit it.")]
    Path("lessons.json").write_text(json.dumps(lessons, indent=2) + "\n")
    reloaded = json.loads(Path("lessons.json").read_text())
    reuse = run_agents(training[2], reference, reloaded)
    save("lesson_reuse.json", reuse)
    candidate = lesson("lesson_002", "Unsupported values for unknown fields",
                       "For a requested field missing from the reference, return JSON null rather than assuming a housing policy.")
    validation_result = validate_lesson(reference, validation, reloaded, candidate)
    save("lesson_validation.json", validation_result)
    selected = validation_result["lessons_after"] if validation_result["accepted"] else reloaded
    Path("lessons.json").write_text(json.dumps(selected, indent=2) + "\n")
    log("lesson_selection_finished", accepted=validation_result["accepted"], kept=[row["lesson_id"] for row in selected])

    # The held-out inputs are first loaded only after development and selection.
    test_bytes = Path("test_data.json").read_bytes()
    test_hash = hashlib.sha256(test_bytes).hexdigest()
    test = json.loads(test_bytes)
    variants = [("Baseline", [], False), ("Evaluator Repair", [], True),
                ("Lesson Memory", reloaded, True), ("Validated Improvement", selected, True)]
    results = {}
    for name, memory, repair in variants:
        independent_memory = copy.deepcopy(memory)
        rows = [run_agents(item, reference, independent_memory, repair=repair) for item in test]
        assert hashlib.sha256(Path("test_data.json").read_bytes()).hexdigest() == test_hash
        results[name] = {"rows": rows, "test_sha256": test_hash,
                         "correct": sum(row["final_evaluation"] == "PASS" for row in rows),
                         "incorrect": sum(row["final_evaluation"] != "PASS" for row in rows),
                         "average_attempts": sum(row["number_attempts"] for row in rows) / len(rows),
                         "average_latency_ms": round(sum(row["latency_ms"] for row in rows) / len(rows), 3),
                         "lesson_state_after": independent_memory}
        save("agent_variants.json", results)
        log("variant_summary", variant=name, **{key: value for key, value in results[name].items() if key not in ("rows", "lesson_state_after")})


if __name__ == "__main__":
    main()
