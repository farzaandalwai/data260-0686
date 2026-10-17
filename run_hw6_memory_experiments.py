"""Run the fixed, isolated HW6 memory-cost experiment."""

from dataclasses import asdict
import json
from pathlib import Path
from statistics import mean

import yaml

from hw6_config import ROOT, settings
from hw6_memory_service import RuntimeMemoryConfig, chat_turn, clean_owned_user
from hw6_schemas import ChatRequest


RAW = ROOT / "reports" / "hw06" / "raw"
PROBES_PATH = ROOT / "memory_probes.yaml"

CONVERSATION = [
    "I want my rental search centered in Santa Clara, California.",
    "My maximum monthly budget is $3,500, and I need you to treat that as a hard cap.",
    "I prefer a two-bedroom apartment rather than a house or studio.",
    "I work near downtown San Jose three days each week.",
    "I need my commute to stay under 30 minutes.",
    "I prefer a walkable neighborhood for groceries and coffee.",
    "I want one covered parking space.",
    "I prefer an in-unit washer and dryer.",
    "I need a quiet building after 10 PM.",
    "I prefer natural light and a balcony.",
    "I want an unfurnished rental.",
    "I prefer a 12-month lease with a renewal option.",
    "I need a smoke-free property because smoke bothers me.",
    "I have one indoor cat, so the rental must allow cats.",
    "I prefer water to be included in the rent.",
    "I want an application fee under $60.",
    "I can pay a security deposit up to one month of rent.",
    "I do not plan to have a roommate.",
    "I prefer the second floor or higher.",
    "I need an elevator if the unit is above the second floor.",
    "I prefer to live near light rail.",
    "I want grocery stores within walking distance.",
    "I prefer air conditioning, but it is not a hard requirement.",
    "I need reliable high-speed internet options for remote work.",
    "I prefer a building with secure package storage.",
    "I want at least 850 square feet if possible.",
    "I prefer a kitchen with a dishwasher.",
    "I need the lease to permit one indoor cat without a monthly pet rent over $50.",
    "I want to move on December 1, 2026.",
    "I can attend property viewings on Saturday mornings.",
]


CONDITIONS = [
    ("SHORT_TERM_N=4", RuntimeMemoryConfig(short_term_n=4, policy="sliding", include_file_memory=False)),
    ("SHORT_TERM_N=12", RuntimeMemoryConfig(short_term_n=12, policy="sliding", include_file_memory=False)),
    ("SHORT_TERM_N=30", RuntimeMemoryConfig(short_term_n=30, policy="sliding", include_file_memory=False)),
    ("relevance_aware_eviction", RuntimeMemoryConfig(short_term_n=12, policy="relevance_aware", include_file_memory=False)),
]


def score_answer(answer: str, probe: dict) -> tuple[int, list[str], list[str], str]:
    lower = answer.lower()
    matched = []
    missing = []
    for criterion in probe["expected_criteria"]:
        if any(phrase.lower() in lower for phrase in criterion["any_of"]):
            matched.append(criterion["label"])
        else:
            missing.append(criterion["label"])
    ratio = len(matched) / len(probe["expected_criteria"])
    if ratio == 1:
        score = 5
    elif ratio >= 0.75:
        score = 4
    elif ratio >= 0.5:
        score = 3
    elif ratio > 0:
        score = 2
    else:
        score = 1
    explanation = (
        f"Objective phrase match: {len(matched)}/{len(probe['expected_criteria'])}; "
        f"matched={matched or ['none']}; missing={missing or ['none']}."
    )
    return score, matched, missing, explanation


def record_response(phase: str, number: int, message: str, response: dict) -> dict:
    return {
        "phase": phase,
        "number": number,
        "message": message,
        "reply": response["reply"],
        "usage": response["usage"],
        "memory_used": {
            "short_term_count": response["memory_used"]["short_term_count"],
            "episodic_facts": response["memory_used"]["episodic_facts"],
            "session_summary_present": bool(response["memory_used"]["session_summary"]),
            "lifetime_summary_present": bool(response["memory_used"]["lifetime_summary"]),
        },
    }


def run_condition(name: str, runtime: RuntimeMemoryConfig, probes: list[dict]) -> dict:
    slug = name.lower().replace("=", "-").replace("_", "-")
    user_id = f"exp-{settings.verify_seed}-{slug}"
    session_id = f"session-{settings.verify_seed}-{slug}"
    clean_owned_user(user_id)
    conversation_rows = []
    for number, message in enumerate(CONVERSATION, start=1):
        response = chat_turn(
            ChatRequest(user_id=user_id, session_id=session_id, message=message),
            runtime=runtime,
            condition=name,
        )
        conversation_rows.append(record_response("conversation", number, message, response))
        print(name, "conversation", number, "prompt", response["usage"]["prompt_tokens"], flush=True)

    probe_rows = []
    for number, probe in enumerate(probes, start=1):
        response = chat_turn(
            ChatRequest(user_id=user_id, session_id=session_id, message=probe["question"]),
            runtime=runtime,
            condition=name + "-probe",
        )
        score, matched, missing, explanation = score_answer(response["reply"], probe)
        row = record_response("probe", number, probe["question"], response)
        row.update({
            "probe_id": probe["id"],
            "expected_criteria": probe["expected_criteria"],
            "score": score,
            "matched": matched,
            "missing": missing,
            "scoring_explanation": explanation,
        })
        probe_rows.append(row)
        print(name, "probe", number, "score", score, flush=True)

    metrics = {
        "condition": name,
        "configuration": asdict(runtime),
        "runs": 1,
        "conversation_turns": len(conversation_rows),
        "probe_turns": len(probe_rows),
        "mean_prompt_tokens": round(mean(row["usage"]["prompt_tokens"] for row in conversation_rows), 3),
        "mean_completion_tokens": round(mean(row["usage"]["completion_tokens"] for row in conversation_rows), 3),
        "mean_latency_ms": round(mean(row["usage"]["latency_ms"] for row in conversation_rows), 3),
        "mean_probe_score": round(mean(row["score"] for row in probe_rows), 3),
    }
    return {
        "condition": name,
        "user_id": user_id,
        "session_id": session_id,
        "configuration": asdict(runtime),
        "conversation": conversation_rows,
        "probes": probe_rows,
        "metrics": metrics,
    }


def projected_cost(metrics: dict) -> dict:
    requests = 10_000 * 30
    input_cost = metrics["mean_prompt_tokens"] * requests / 1_000_000 * 1
    output_cost = metrics["mean_completion_tokens"] * requests / 1_000_000 * 5
    return {
        "condition": metrics["condition"],
        "requests": requests,
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(input_cost + output_cost, 4),
    }


def write_metrics(results: list[dict], policy: dict, costs: list[dict], selection: dict) -> None:
    lines = [
        "# HW6 Memory-Cost Metrics",
        "",
        f"Model: `{settings.ollama_model}` at temperature 0.0",
        f"Embedding: `{settings.embedding_model}` (local, 384 dimensions)",
        "Component token counts: MiniLM WordPiece estimates; total prompt/completion counts are exact Ollama counts.",
        "Each condition used one isolated 30-turn run followed by the same five probes.",
        "Part 4 file memory was disabled in every condition so it could not distort the MongoDB window comparison.",
        "",
        "## Required comparison",
        "",
        "| Setting | Mean prompt tokens/turn | Mean completion tokens/turn | Mean latency (ms) | Probe quality (1-5) | Runs/turns |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        item = result["metrics"]
        lines.append(
            f"| {item['condition']} | {item['mean_prompt_tokens']:.3f} | "
            f"{item['mean_completion_tokens']:.3f} | {item['mean_latency_ms']:.3f} | "
            f"{item['mean_probe_score']:.3f} | 1 / 30 + 5 probes |"
        )
    lines.extend([
        "",
        "## Relevance-aware eviction versus SHORT_TERM_N=30",
        "",
        f"- Absolute prompt-token savings: {policy['absolute_prompt_token_savings']:.3f} tokens/turn",
        f"- Percentage prompt-token savings: {policy['percentage_prompt_token_savings']:.3f}%",
        f"- Probe-quality change: {policy['probe_score_change']:+.3f} points",
        f"- Latency change: {policy['latency_change_ms']:+.3f} ms",
        "",
        "## Cost estimate for 10,000 x 30-turn conversations",
        "",
        "| Setting | Input cost | Output cost | Total cost |",
        "|---|---:|---:|---:|",
    ])
    for cost in costs:
        lines.append(
            f"| {cost['condition']} | ${cost['input_cost_usd']:.4f} | "
            f"${cost['output_cost_usd']:.4f} | ${cost['total_cost_usd']:.4f} |"
        )
    lines.extend([
        "",
        "## Selection rule",
        "",
        selection["rule"],
        "",
        f"Best: **{selection['best']}**. Worst: **{selection['worst']}**.",
        "",
    ])
    (ROOT / "reports" / "hw06" / "METRICS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    probe_data = yaml.safe_load(PROBES_PATH.read_text(encoding="utf-8"))
    probes = probe_data["probes"]
    if len(probes) != 5:
        raise RuntimeError("memory_probes.yaml must contain exactly five probes")
    results = [run_condition(name, runtime, probes) for name, runtime in CONDITIONS]
    metrics = [result["metrics"] for result in results]
    by_name = {item["condition"]: item for item in metrics}
    baseline = by_name["SHORT_TERM_N=30"]
    eviction = by_name["relevance_aware_eviction"]
    savings = baseline["mean_prompt_tokens"] - eviction["mean_prompt_tokens"]
    policy = {
        "baseline": "SHORT_TERM_N=30",
        "policy": "relevance_aware_eviction",
        "absolute_prompt_token_savings": round(savings, 3),
        "percentage_prompt_token_savings": round(savings / baseline["mean_prompt_tokens"] * 100, 3),
        "probe_score_change": round(eviction["mean_probe_score"] - baseline["mean_probe_score"], 3),
        "latency_change_ms": round(eviction["mean_latency_ms"] - baseline["mean_latency_ms"], 3),
    }
    costs = [projected_cost(item) for item in metrics]
    cost_by_name = {item["condition"]: item for item in costs}
    highest_quality = max(item["mean_probe_score"] for item in metrics)
    eligible = [item for item in metrics if item["mean_probe_score"] >= highest_quality - 0.5]
    best = min(eligible, key=lambda item: cost_by_name[item["condition"]]["total_cost_usd"])
    same_quality = [item for item in metrics if item["mean_probe_score"] >= highest_quality - 0.5]
    if same_quality:
        worst = max(same_quality, key=lambda item: cost_by_name[item["condition"]]["total_cost_usd"])
    else:
        worst = min(metrics, key=lambda item: item["mean_probe_score"])
    selection = {
        "rule": (
            "Best is the lowest projected-cost configuration within 0.5 points of the highest "
            "probe score. Worst is the highest-cost configuration in that same quality band; "
            "if none share the band, it is the objectively lowest-quality configuration."
        ),
        "best": best["condition"],
        "worst": worst["condition"],
    }

    filenames = {
        "SHORT_TERM_N=4": "short_term_n_4.json",
        "SHORT_TERM_N=12": "short_term_n_12.json",
        "SHORT_TERM_N=30": "short_term_n_30.json",
        "relevance_aware_eviction": "relevance_aware_policy.json",
    }
    for result in results:
        (RAW / filenames[result["condition"]]).write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    all_probes = [
        {"condition": result["condition"], **probe}
        for result in results for probe in result["probes"]
    ]
    (RAW / "memory_probe_scores.json").write_text(
        json.dumps({"rubric": probe_data["rubric"], "results": all_probes}, indent=2) + "\n",
        encoding="utf-8",
    )
    payload = {
        "seed": settings.seed,
        "verify_seed": settings.verify_seed,
        "fixed_conversation": CONVERSATION,
        "condition_metrics": metrics,
        "policy_comparison": policy,
        "costs": costs,
        "selection": selection,
        "file_memory_during_sweep": "disabled for every condition",
    }
    (RAW / "memory_experiment_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (RAW / "cost_calculations.json").write_text(
        json.dumps({"costs": costs, "selection": selection}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_metrics(results, policy, costs, selection)
    print(json.dumps(payload["condition_metrics"], indent=2))


if __name__ == "__main__":
    main()
