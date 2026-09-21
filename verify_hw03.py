import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path

import yaml


SID4 = "0686"
PORT_BASE = 8686
PREFIX = "s0686"
SEED = 686
VERIFY_SEED = 260686
DOMAIN_ID = 6

reports_path = Path("reports/hw03")
corpus_path = Path("corpus/hw03")
verification_path = reports_path / "verification.json"

expected_corpus = [
    "california_tenants_2026.pdf",
    "cfpb_tenant_background_consumer_snapshot.pdf",
    "cfpb_tenant_background_market_report.pdf",
    "ftc_rental_listing_scams.html",
    "ftc_rental_scams_data_spotlight.html",
    "hud_rental_screening_guidance.pdf",
]

required_files = [
    reports_path / "RUN_LOG.txt",
    reports_path / "METRICS.md",
    reports_path / "AI_USE.md",
    reports_path / "SOURCES.md",
    reports_path / "CORPUS_MANIFEST.json",
    reports_path / "questions.yaml",
    reports_path / "raw" / "retrieval_runs.json",
    reports_path / "raw" / "retrieval_runs.csv",
    reports_path / "raw" / "chunk_stats.json",
    Path("part2_retrieval.py"),
    Path("summarize_hw03_results.py"),
    Path("routers/auth.py"),
    Path("templates/home.html"),
    Path("templates/login.html"),
    Path("templates/dashboard.html"),
]

screenshots = [
    "part1_home_logged_out.png",
    "part1_login.png",
    "part1_invalid_login.png",
    "part1_dashboard.png",
    "part1_home_logged_in.png",
    "part1_cookie_header.png",
    "part1_logged_out_dashboard_denied.png",
    "part1_session_expired.png",
    "part1_templates_directory.png",
]

expected_chunk_stats = {
    "TokenTextSplitter": {"chunks": 839, "avg_chunk_length": 1042.78},
    "SemanticSplitterNodeParser": {"chunks": 286, "avg_chunk_length": 2676.38},
    "SentenceWindowNodeParser": {"chunks": 5538, "avg_chunk_length": 138.22},
}

metric_rows = [
    "| TokenTextSplitter | 839 | 1042.78 | 0.673236 | 0.645124 | 1.0 | 12.14 |",
    "| SemanticSplitterNodeParser | 286 | 2676.38 | 0.575736 | 0.565879 | 1.0 | 7.48 |",
    "| SentenceWindowNodeParser | 5538 | 138.22 | 0.747511 | 0.646602 | 1.0 | 47.62 |",
]


def file_is_nonempty(path):
    return path.is_file() and path.stat().st_size > 0


checks = {}

readme_text = Path("README.md").read_text() if Path("README.md").exists() else ""
checks["sid4"] = f"SID4: {SID4}" in readme_text and SID4 == "0686"
checks["port_base"] = f"PORT_BASE: {PORT_BASE}" in readme_text and PORT_BASE == 8686
checks["prefix"] = f"PREFIX: {PREFIX}" in readme_text and PREFIX == "s0686"
checks["seed"] = f"SEED: {SEED}" in readme_text and SEED == 686
checks["verify_seed"] = f"VERIFY_SEED: {VERIFY_SEED}" in readme_text and VERIFY_SEED == 260686
checks["domain_id"] = f"DOMAIN_ID: {DOMAIN_ID}" in readme_text and DOMAIN_ID == 6

checks["reports_directory"] = reports_path.is_dir()
checks["required_files"] = all(path.exists() for path in required_files)

questions_path = reports_path / "questions.yaml"
questions = yaml.safe_load(questions_path.read_text()) if questions_path.exists() else []
checks["questions_count"] = isinstance(questions, list) and len(questions) == 5

corpus_files = []
if corpus_path.is_dir():
    corpus_files = sorted(path.name for path in corpus_path.iterdir() if path.is_file())
corpus_bytes = sum((corpus_path / name).stat().st_size for name in corpus_files)
checks["corpus_files"] = corpus_files == sorted(expected_corpus)
checks["corpus_size"] = corpus_bytes >= 200 * 1024

runs_path = reports_path / "raw" / "retrieval_runs.json"
run_count = 0
if runs_path.exists():
    retrieval_data = json.loads(runs_path.read_text())
    run_count = sum(len(results) for results in retrieval_data["chunkers"].values())
checks["retrieval_runs"] = run_count == 15

csv_path = reports_path / "raw" / "retrieval_runs.csv"
csv_rows = 0
if csv_path.exists():
    with csv_path.open(newline="") as file:
        csv_rows = sum(1 for _ in csv.DictReader(file))
checks["retrieval_rows"] = csv_rows == 75

stats_path = reports_path / "raw" / "chunk_stats.json"
chunk_stats_match = False
if stats_path.exists():
    chunk_stats = json.loads(stats_path.read_text())
    chunk_stats_match = all(
        technique in chunk_stats
        and chunk_stats[technique]["chunks"] == expected["chunks"]
        and round(chunk_stats[technique]["avg_chunk_length"], 2) == expected["avg_chunk_length"]
        for technique, expected in expected_chunk_stats.items()
    )
checks["chunk_stats"] = chunk_stats_match

metrics_text = (reports_path / "METRICS.md").read_text() if (reports_path / "METRICS.md").exists() else ""
checks["metrics_table"] = all(row in metrics_text for row in metric_rows)
checks["wrong_retrieval_example"] = "cfpb_tenant_background_market_report.pdf" in metrics_text and "hud_rental_screening_guidance.pdf" in metrics_text

checks["auth_router"] = Path("routers/auth.py").is_file()
checks["templates"] = all(
    file_is_nonempty(Path("templates") / name)
    for name in ["home.html", "login.html", "dashboard.html"]
)
checks["part1_screenshots"] = all(
    file_is_nonempty(reports_path / "screenshots" / name) for name in screenshots
)
checks["part2_retrieval_script"] = Path("part2_retrieval.py").is_file()
checks["summary_script"] = Path("summarize_hw03_results.py").is_file()

questions_diff = subprocess.check_output(
    ["git", "diff", "def106c", "--", "reports/hw03/questions.yaml"],
    text=True,
)
checks["questions_frozen"] = questions_diff.strip() == ""

result = {
    "verify_seed": VERIFY_SEED,
    "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    "overall_pass": all(checks.values()),
    "checks": checks,
}

reports_path.mkdir(parents=True, exist_ok=True)
verification_path.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
