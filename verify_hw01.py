import json
import os

checks = {
    "index_html_exists": os.path.exists("index.html"),
    "script_js_exists": os.path.exists("script.js"),
    "domain_schema_exists": os.path.exists("DOMAIN_SCHEMA.md"),
    "agents_demo_exists": os.path.exists("agents_demo.py"),
    "model_client_exists": os.path.exists("src/model_client.py"),
    "hw1_client_exists": os.path.exists("hw1_client.py"),
    "agent_md_exists": os.path.exists("AGENT.md"),
    "nondeterminism_input_exists": os.path.exists(
        "reports/hw01/cases/nondeterminism_input.json"
    ),
    "part3_json_exists": os.path.exists(
        "reports/hw01/raw/part3_runs.json"
    ),
    "part3_csv_exists": os.path.exists(
        "reports/hw01/raw/part3_runs.csv"
    ),
    "part4_tokens_exists": os.path.exists(
        "reports/hw01/raw/part4_tokens.json"
    ),
    "metrics_exists": os.path.exists(
        "reports/hw01/METRICS.md"
    ),
    "run_log_exists": os.path.exists(
        "reports/hw01/RUN_LOG.txt"
    ),
    "ai_use_exists": os.path.exists(
        "reports/hw01/AI_USE.md"
    )
}

result = {
    "passed": all(checks.values()),
    "checks": checks
}

with open("reports/hw01/verification.json", "w") as file:
    json.dump(result, file, indent=2)

print(json.dumps(result, indent=2))