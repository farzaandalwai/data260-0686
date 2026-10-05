import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

from sqlalchemy import text

from database import SessionLocal


VERIFY_SEED = 260686
TIMEOUT_SECONDS = 0.75
MAX_ATTEMPTS = 3
BASE_DELAY = 0.02
MAX_DELAY = 0.08
CALLS_PER_RATE = 50
RATES = (0.0, 0.20, 0.50)
RAW = Path("reports/hw05/raw")


def read_listing_count():
    with SessionLocal() as db:
        return db.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()


def failure_plan(seed, rate):
    rng = random.Random(seed)
    plan = []
    for _ in range(CALLS_PER_RATE):
        plan.append([rng.random() < rate for _ in range(MAX_ATTEMPTS)])
    return plan


def call_once(operation, timeout_s):
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(operation)
        return future.result(timeout=timeout_s)


def run_with_retry(operation, failures, timeout_s=TIMEOUT_SECONDS):
    started = time.perf_counter()
    attempts = []
    for number, failed in enumerate(failures, start=1):
        attempt_started = time.perf_counter()
        error = None
        try:
            if failed:
                raise RuntimeError("injected failure")
            call_once(operation, timeout_s)
        except FuturesTimeout:
            error = "attempt timed out"
        except Exception as exc:
            error = str(exc)
        attempts.append({
            "attempt": number,
            "ok": error is None,
            "error": error,
            "latency_ms": (time.perf_counter() - attempt_started) * 1000,
        })
        if error is None or number == len(failures):
            break
        delay = min(BASE_DELAY * (2 ** (number - 1)), MAX_DELAY)
        time.sleep(delay)
    ok = attempts[-1]["ok"]
    return {
        "ok": ok,
        "error": None if ok else attempts[-1]["error"],
        "attempts_used": len(attempts),
        "attempts": attempts,
        "latency_ms": (time.perf_counter() - started) * 1000,
    }


def percentile(values, percent):
    ordered = sorted(values)
    rank = math.ceil(percent / 100 * len(ordered))
    return ordered[rank - 1]


def summarize(rate, records):
    latencies = [record["latency_ms"] for record in records]
    successes = sum(1 for record in records if record["ok"])
    return {
        "rate": rate,
        "calls": len(records),
        "successes": successes,
        "success_rate": successes / len(records),
        "mean_latency_ms": sum(latencies) / len(latencies),
        "p99_latency_ms": percentile(latencies, 99),
    }


def demo_operation():
    return "ok"


def slow_operation():
    time.sleep(TIMEOUT_SECONDS + 0.25)
    return "late"


def main():
    demos = {
        "first_attempt_success": run_with_retry(demo_operation, [False]),
        "retry_then_success": run_with_retry(demo_operation, [True, False]),
        "all_retries_fail": run_with_retry(demo_operation, [True, True, True]),
        "timeout": run_with_retry(slow_operation, [False], timeout_s=0.2),
    }
    records = []
    summaries = []
    reproduced = True
    for rate in RATES:
        plan = failure_plan(VERIFY_SEED, rate)
        reproduced = reproduced and plan == failure_plan(VERIFY_SEED, rate)
        for call_number, failures in enumerate(plan, start=1):
            result = run_with_retry(read_listing_count, failures)
            records.append({
                "seed": VERIFY_SEED,
                "rate": rate,
                "call": call_number,
                "failure_plan": failures,
                "ok": result["ok"],
                "error": result["error"],
                "attempts_used": result["attempts_used"],
                "latency_ms": result["latency_ms"],
            })
        summaries.append(summarize(rate, records[-CALLS_PER_RATE:]))
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "part3_calls.json").write_text(json.dumps(records, indent=2) + "\n")
    (RAW / "part3_retry_demos.json").write_text(json.dumps(demos, indent=2) + "\n")
    summary = {
        "verify_seed": VERIFY_SEED,
        "calls_per_rate": CALLS_PER_RATE,
        "max_attempts": MAX_ATTEMPTS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "base_delay_seconds": BASE_DELAY,
        "max_delay_seconds": MAX_DELAY,
        "plan_reproduced": reproduced,
        "rates": summaries,
    }
    (RAW / "part3_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print("demo_ok", {name: item["ok"] for name, item in demos.items()})
    print("records", len(records))


if __name__ == "__main__":
    main()
