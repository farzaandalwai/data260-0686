import csv
import json
import os
import py_compile
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml
from sqlalchemy import text


SID4 = "0686"
PORT_BASE = 8686
PREFIX = "s0686"
SEED = 686
VERIFY_SEED = 260686
DOMAIN_ID = 6
REFUSAL = "I cannot answer this question from the provided documents"

root = Path(__file__).resolve().parent
os.chdir(root)

reports_path = Path("reports/hw04")
raw_path = reports_path / "raw"
verification_path = reports_path / "verification.json"

source_files = [
    Path("main.py"),
    Path("database.py"),
    Path("models.py"),
    Path("seed_hw04_user.py"),
    Path("seed_hw04_data.py"),
    Path("benchmark_hw04_nplus1.py"),
    Path("add_hw04_index.py"),
    Path("rag.py"),
    Path("routers/hw4_auth.py"),
    Path("routers/hw4_listings.py"),
    Path("routers/hw4_measure.py"),
    Path("client/src/App.jsx"),
    Path("client/src/pages/Login.jsx"),
    Path("client/src/pages/Home.jsx"),
    Path("client/src/pages/CreateRecord.jsx"),
    Path("client/src/pages/UpdateRecord.jsx"),
    Path("client/src/pages/DeleteRecord.jsx"),
]

report_files = [
    reports_path / "RUN_LOG.txt",
    reports_path / "METRICS.md",
    reports_path / "AI_USE.md",
    reports_path / "RAG_ANALYSIS.md",
    reports_path / "questions.yaml",
    raw_path / "nplus1_runs.json",
    raw_path / "nplus1_runs.csv",
    raw_path / "nplus1_summary.json",
    raw_path / "explain_before.json",
    raw_path / "explain_after.json",
    raw_path / "rag_retrievals.json",
    raw_path / "rag_retrieval_check.json",
    raw_path / "rag_comparison.json",
    raw_path / "rag_comparison.csv",
    raw_path / "rag_k_sweep.json",
    raw_path / "rag_evaluation.csv",
    raw_path / "rag_evaluation.json",
]

screenshot_files = [
    "HW4-DB-01.png",
    "HW4-STRUCTURE-01.png",
    "HW4-SCHEMA-01.png",
    "HW4-SCHEMA-02.png",
    "HW4-SCHEMA-03.png",
    "HW4-AUTH-01.png",
    "HW4-AUTH-02.png",
    "HW4-AUTH-03.png",
    "HW4-AUTH-04.png",
    "HW4-CRUD-AUTH-01.png",
    "HW4-CRUD-PERSISTENCE-01.png",
    "HW4-POSTMAN-POST.png",
    "HW4-POSTMAN-GET-ALL.png",
    "HW4-POSTMAN-GET-ID.png",
    "HW4-POSTMAN-PUT.png",
    "HW4-POSTMAN-DELETE.png",
    "HW4-REACT-LOGIN-REQUIRED.png",
    "HW4-REACT-ROUTE-GUARD.png",
    "HW4-REACT-LOGIN.png",
    "HW4-REACT-CREATE.png",
    "HW4-REACT-HOME.png",
    "HW4-REACT-UPDATE.png",
    "HW4-REACT-AFTER-UPDATE.png",
    "HW4-REACT-DELETE.png",
    "HW4-REACT-AFTER-DELETE.png",
    "HW4-SEED-01.png",
    "HW4-NPLUS1-NAIVE-10.png",
    "HW4-NPLUS1-FIXED-10.png",
    "HW4-NPLUS1-NAIVE-50.png",
    "HW4-NPLUS1-FIXED-50.png",
    "HW4-NPLUS1-NAIVE-200.png",
    "HW4-NPLUS1-FIXED-200.png",
    "HW4-BENCHMARK-01.png",
    "HW4-BENCHMARK-RAW-01.png",
    "HW4-INDEX-BEFORE.png",
    "HW4-INDEX-AFTER.png",
    "HW4-RAG-SETUP-01.png",
    "HW4-RAG-RETRIEVAL-Q1-Q3.png",
    "HW4-RAG-RETRIEVAL-Q4-Q6.png",
    "HW4-RAG-COMPARE-Q1-Q3.png",
    "HW4-RAG-COMPARE-Q4-Q6.png",
    "HW4-RAG-CONTEXT-01.png",
    "HW4-RAG-K-SWEEP.png",
    "HW4-RAG-EVALUATION.png",
]

hw3_files = [
    Path("part2_retrieval.py"),
    Path("routers/auth.py"),
    Path("reports/hw03/questions.yaml"),
    Path("reports/hw03/METRICS.md"),
    Path("reports/hw03/raw/retrieval_runs.json"),
    Path("reports/hw03/raw/retrieval_runs.csv"),
    Path("corpus/hw03/california_tenants_2026.pdf"),
    Path("corpus/hw03/cfpb_tenant_background_consumer_snapshot.pdf"),
    Path("corpus/hw03/cfpb_tenant_background_market_report.pdf"),
    Path("corpus/hw03/ftc_rental_listing_scams.html"),
    Path("corpus/hw03/ftc_rental_scams_data_spotlight.html"),
    Path("corpus/hw03/hud_rental_screening_guidance.pdf"),
]

compile_files = [
    "main.py",
    "database.py",
    "models.py",
    "seed_hw04_user.py",
    "seed_hw04_data.py",
    "benchmark_hw04_nplus1.py",
    "add_hw04_index.py",
    "rag.py",
    "routers/hw4_auth.py",
    "routers/hw4_listings.py",
    "routers/hw4_measure.py",
]

group_counts = {
    (10, "naive"): 30,
    (10, "fixed"): 30,
    (50, "naive"): 30,
    (50, "fixed"): 30,
    (200, "naive"): 30,
    (200, "fixed"): 30,
}

json_names = [
    "nplus1_runs.json",
    "nplus1_summary.json",
    "explain_before.json",
    "explain_after.json",
    "rag_retrievals.json",
    "rag_retrieval_check.json",
    "rag_comparison.json",
    "rag_k_sweep.json",
    "rag_evaluation.json",
]


def load_json(path):
    return json.loads(path.read_text())


def png_ok(path):
    if not path.is_file() or path.stat().st_size < 20000:
        return False
    return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


checks = {}

readme_text = Path("README.md").read_text() if Path("README.md").exists() else ""
checks["sid4"] = f"SID4: {SID4}" in readme_text and SID4 == "0686"
checks["port_base"] = f"PORT_BASE: {PORT_BASE}" in readme_text and PORT_BASE == 8686
checks["prefix"] = f"PREFIX: {PREFIX}" in readme_text and PREFIX == "s0686"
checks["seed"] = f"SEED: {SEED}" in readme_text and SEED == 686
checks["verify_seed"] = f"VERIFY_SEED: {VERIFY_SEED}" in readme_text and VERIFY_SEED == 260686
checks["domain_id"] = f"DOMAIN_ID: {DOMAIN_ID}" in readme_text and DOMAIN_ID == 6

database_text = Path("database.py").read_text() if Path("database.py").exists() else ""
checks["engine_variable"] = (
    "db_engine = create_engine" in database_text
    and "bind=db_engine" in database_text
)

checks["source_files"] = all(path.is_file() for path in source_files)
checks["report_files"] = all(path.is_file() and path.stat().st_size > 0 for path in report_files)
checks["screenshots"] = all(png_ok(reports_path / "screenshots" / name) for name in screenshot_files)
app_source = Path("client/src/App.jsx").read_text() if Path("client/src/App.jsx").exists() else ""
checks["crud_route_guard"] = (
    "function LoginRequired()" in app_source
    and "Login required" in app_source
    and 'to="/login"' in app_source
    and "loading ?" in app_source
    and app_source.count("user ?") >= 5
)
checks["hw3_paths"] = all(path.is_file() and path.stat().st_size > 0 for path in hw3_files)

ai_text = (reports_path / "AI_USE.md").read_text() if (reports_path / "AI_USE.md").exists() else ""
checks["ai_use_completed"] = len(ai_text.split()) >= 120 and "What did you use an AI assistant for" in ai_text

parsed = {}
json_ok = True
for name in json_names:
    try:
        parsed[name] = load_json(raw_path / name)
    except (OSError, json.JSONDecodeError):
        json_ok = False
checks["json_parses"] = json_ok and len(parsed) == len(json_names)

runs = parsed.get("nplus1_runs.json")
run_groups = Counter()
if isinstance(runs, list):
    run_groups = Counter((row.get("page_size"), row.get("version")) for row in runs)
checks["nplus1_json_count"] = isinstance(runs, list) and len(runs) == 180
checks["nplus1_json_groups"] = run_groups == group_counts

csv_rows = []
csv_path = raw_path / "nplus1_runs.csv"
if csv_path.exists():
    with csv_path.open(newline="") as file:
        csv_rows = list(csv.DictReader(file))
csv_groups = Counter((int(row["page_size"]), row["version"]) for row in csv_rows) if csv_rows else Counter()
checks["nplus1_csv_count"] = len(csv_rows) == 180
checks["nplus1_csv_groups"] = csv_groups == group_counts

summary = parsed.get("nplus1_summary.json")
checks["nplus1_summary"] = isinstance(summary, dict) and summary.get("measured_requests") == 180

comparison = parsed.get("rag_comparison.json")
comparison_rows = comparison.get("rows") if isinstance(comparison, dict) else None
checks["rag_comparison_count"] = isinstance(comparison_rows, list) and len(comparison_rows) == 18

comparison_csv_count = 0
comparison_csv_path = raw_path / "rag_comparison.csv"
if comparison_csv_path.exists():
    with comparison_csv_path.open(newline="") as file:
        comparison_csv_count = sum(1 for _ in csv.DictReader(file))
checks["rag_comparison_csv_count"] = comparison_csv_count == 18

evaluation = parsed.get("rag_evaluation.json")
checks["rag_evaluation_count"] = isinstance(evaluation, list) and len(evaluation) == 18

evaluation_csv_count = 0
evaluation_csv_path = raw_path / "rag_evaluation.csv"
if evaluation_csv_path.exists():
    with evaluation_csv_path.open(newline="") as file:
        evaluation_csv_count = sum(1 for _ in csv.DictReader(file))
checks["rag_evaluation_csv_count"] = evaluation_csv_count == 18

sweep = parsed.get("rag_k_sweep.json")
sweep_runs = sweep.get("runs") if isinstance(sweep, dict) else None
checks["rag_k_sweep_count"] = (
    isinstance(sweep_runs, list)
    and len(sweep_runs) == 3
    and [row.get("k") for row in sweep_runs] == [1, 3, 5]
)

answers = {}
if isinstance(comparison_rows, list):
    answers = {(row.get("question_id"), row.get("configuration")): row.get("answer") for row in comparison_rows}
checks["context_q5_refusal"] = answers.get(("q5", "context_rag")) == REFUSAL
checks["context_q6_refusal"] = answers.get(("q6", "context_rag")) == REFUSAL

analysis_path = reports_path / "RAG_ANALYSIS.md"
analysis_words = len(analysis_path.read_text().split()) if analysis_path.exists() else 0
checks["analysis_word_count"] = 300 <= analysis_words <= 500

questions = []
questions_path = reports_path / "questions.yaml"
if questions_path.exists():
    loaded_questions = yaml.safe_load(questions_path.read_text())
    if isinstance(loaded_questions, list):
        questions = loaded_questions
expected_categories = [
    "one_chunk",
    "two_chunks",
    "similar_across_documents",
    "ambiguous",
    "not_in_documents",
    "unrelated",
]
checks["question_categories"] = [item.get("category") for item in questions] == expected_categories

compile_ok = True
for name in compile_files:
    try:
        py_compile.compile(name, doraise=True)
    except py_compile.PyCompileError:
        compile_ok = False
checks["python_compile"] = compile_ok

try:
    from database import SessionLocal

    db = SessionLocal()
    try:
        database_name = db.execute(text("SELECT DATABASE()")).scalar()
        listing_count = db.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()
        note_count = db.execute(text("SELECT COUNT(*) FROM listing_notes")).scalar()
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        orphan_count = db.execute(
            text(
                "SELECT COUNT(*) FROM listing_notes n "
                "LEFT JOIN rental_listings r ON n.listing_id = r.id "
                "WHERE r.id IS NULL"
            )
        ).scalar()
        index_count = db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'rental_listings' "
                "AND index_name = 'idx_rental_listings_property_title'"
            )
        ).scalar()
    finally:
        db.close()
    checks["database_name"] = database_name == "s0686_rel"
    checks["listing_count"] = listing_count == 5000
    checks["related_count"] = note_count == 200
    checks["users_present"] = user_count >= 1
    checks["orphan_count"] = orphan_count == 0
    checks["index_exists"] = index_count > 0
except Exception:
    checks["database_name"] = False
    checks["listing_count"] = False
    checks["related_count"] = False
    checks["users_present"] = False
    checks["orphan_count"] = False
    checks["index_exists"] = False

tested_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

result = {
    "homework": 4,
    "sid4": SID4,
    "verify_seed": VERIFY_SEED,
    "tested_commit": tested_commit,
    "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    "checks": checks,
    "overall_pass": all(checks.values()),
}

reports_path.mkdir(parents=True, exist_ok=True)
verification_path.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
