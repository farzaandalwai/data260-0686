import copy
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from hw9_cache import log
from src.model_client import complete


class AnsweringAgent:
    def __init__(self, reference: dict, lessons: list[dict]):
        self.reference, self.lessons = reference, lessons

    def answer(self, item: dict, feedback=None, controlled_omission=False) -> dict:
        record = self.reference[str(item["listing_id"])]
        relevant = [lesson for lesson in self.lessons
                    if ("available_units" in lesson["failure_pattern"] and "available_units" in item["fields"])
                    or ("unknown" in lesson["failure_pattern"] and any(field not in record for field in item["fields"]))]
        for lesson in relevant:
            lesson["use_count"] += 1
        log("lessons_loaded", question=item["question"], lesson_ids=[lesson["lesson_id"] for lesson in relevant])
        prompt = {"question": item["question"], "reference_record": record,
                  "requested_fields": ["listing_id", *item["fields"]],
                  "lessons": [lesson["correction"] for lesson in relevant], "evaluator_feedback": feedback}
        result = complete([{"role": "system", "content": "Answer from the supplied rental reference only. Return a JSON object with every requested field. Use null if a fact is not recorded; do not invent facts."},
                           {"role": "user", "content": json.dumps(prompt)}], temperature=0.0, json_output=True, num_predict=160)
        answer = json.loads(result["message"])
        if controlled_omission:
            answer.pop("available_units", None)
            log("controlled_fault", question=item["question"], fault="Intentionally removed available_units after model generation")
        return {"answer": answer, "loaded_lessons": [lesson["lesson_id"] for lesson in relevant], "model": result["model"]}


class EvaluatorAgent:
    def __init__(self, reference: dict):
        self.reference = reference

    def evaluate(self, item: dict, answer: dict) -> dict:
        record = self.reference[str(item["listing_id"])]
        expected = {field: record.get(field) for field in ["listing_id", *item["fields"]]}
        errors = []
        if not isinstance(answer, dict):
            errors.append("Answer must be a JSON object")
        else:
            for field, value in expected.items():
                if field not in answer:
                    errors.append(f"Missing {field}; reference value is {json.dumps(value)}")
                elif answer[field] != value or type(answer[field]) is not type(value):
                    errors.append(f"Incorrect {field}; reference value is {json.dumps(value)}")
            for field, value in answer.items():
                if field not in expected and (field not in record or record[field] != value):
                    errors.append(f"Unsupported extra field {field}")
        return {"result": "REVISE" if errors else "PASS", "feedback": "; ".join(errors) if errors else "Requested facts match the reference"}


def run_agents(item: dict, reference: dict, lessons: list[dict], repair=True, controlled=False) -> dict:
    started = time.perf_counter()
    answering, evaluator = AnsweringAgent(reference, lessons), EvaluatorAgent(reference)
    attempts, feedback = [], None
    for attempt in range(1, 3 if repair else 2):
        generated = answering.answer(item, feedback, controlled_omission=controlled and attempt == 1)
        evaluation = evaluator.evaluate(item, generated["answer"])
        row = {"attempt": attempt, **generated, "evaluation": evaluation}
        attempts.append(row)
        log("agent_attempt", question=item["question"], **row)
        if evaluation["result"] == "PASS":
            break
        feedback = evaluation["feedback"]
    result = {"question": item["question"], "listing_id": item["listing_id"], "attempts": attempts,
              "number_attempts": len(attempts), "final_answer": attempts[-1]["answer"],
              "final_evaluation": attempts[-1]["evaluation"]["result"],
              "latency_ms": round((time.perf_counter() - started) * 1000, 3)}
    log("agents_final", **result)
    return result


def lesson(identifier: str, pattern: str, correction: str) -> dict:
    return {"lesson_id": identifier, "failure_pattern": pattern, "correction": correction,
            "created_at": datetime.now(timezone.utc).isoformat(), "use_count": 0}


def validate_lesson(reference: dict, inputs: list[dict], previous: list[dict], proposed: dict) -> dict:
    before_lessons, after_lessons = copy.deepcopy(previous), copy.deepcopy(previous + [proposed])
    before = [run_agents(item, reference, before_lessons, repair=False) for item in inputs]
    after = [run_agents(item, reference, after_lessons, repair=False) for item in inputs]
    old = [row["final_evaluation"] == "PASS" for row in before]
    new = [row["final_evaluation"] == "PASS" for row in after]
    no_regressions = all(not correct or new[index] for index, correct in enumerate(old))
    failures_no_worse = sum(new[index] for index, correct in enumerate(old) if not correct) >= 0
    unrelated_supported = all(new[index] for index, item in enumerate(inputs) if "available_units" not in item["fields"])
    return {"before": before, "after": after, "no_regressions": no_regressions,
            "failure_cases_no_worse": failures_no_worse, "unrelated_supported": unrelated_supported,
            "accepted": no_regressions and failures_no_worse and unrelated_supported,
            "candidate": proposed, "lessons_after": after_lessons}


def load_reference() -> dict:
    return json.loads(Path("hw9_reference.json").read_text())
