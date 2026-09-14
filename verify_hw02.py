import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


sys.dont_write_bytecode = True

from src.model_client import MODEL


SID4 = "0686"
SEED = 686
VERIFY_SEED = 260686
PORT_BASE = 8686
PREFIX = "s0686"
DOMAIN_ID = 6

reports_path = Path("reports/hw02")
verification_path = reports_path / "verification.json"
checks = {}


def add_check(name, passed, detail=""):
    checks[name] = {
        "status": "PASS" if passed else "FAIL",
        "passed": bool(passed),
        "detail": detail,
    }


required_files = [
    "main.py",
    "agent_graph.py",
    "src/model_client.py",
    "part4_experiment.py",
    "requirements.txt",
    "reports/hw02/RUN_LOG.txt",
    "reports/hw02/METRICS.md",
    "reports/hw02/AI_USE.md",
    "reports/hw02/cases/schema_input.json",
    "reports/hw02/cases/adversarial_input.json",
    "reports/hw02/raw/schema_validation_runs.json",
    "reports/hw02/raw/schema_validation_runs.csv",
    "reports/hw02/raw/ceiling_2_runs.json",
    "reports/hw02/raw/ceiling_2_runs.csv",
    "reports/hw02/raw/ceiling_10_runs.json",
    "reports/hw02/raw/ceiling_10_runs.csv",
    "reports/hw02/raw/adversarial_runs.json",
    "reports/hw02/raw/adversarial_runs.csv",
]
missing_files = [path for path in required_files if not Path(path).exists()]
add_check(
    "required_files",
    not missing_files,
    "All required files exist" if not missing_files else str(missing_files),
)


try:
    import main as api_module
    from fastapi.testclient import TestClient

    add_check("fastapi_import", True, "FastAPI app imported")

    api_module.listings.clear()
    api_module.next_id = 1

    first_listing = {
        "propertyTitle": "Sunny Apartment",
        "location": "San Jose",
        "submitterEmail": "verify1@example.com",
        "description": "Bright apartment with parking near downtown San Jose.",
        "propertyType": "Apartment",
        "termsAccepted": True,
    }
    second_listing = {
        "propertyTitle": "Downtown Loft",
        "location": "Oakland",
        "submitterEmail": "verify2@example.com",
        "description": "Modern downtown loft with large windows and secure parking.",
        "propertyType": "Condominium",
        "termsAccepted": True,
    }

    with TestClient(api_module.app) as client:
        response = client.get("/listings")
        add_check(
            "fastapi_get_listings",
            response.status_code == 200,
            f"Status {response.status_code}",
        )

        first_response = client.post("/listings", json=first_listing)
        second_response = client.post("/listings", json=second_listing)
        created = first_response.json()
        add_check(
            "fastapi_post_listing",
            first_response.status_code == 201
            and second_response.status_code == 201,
            f"Statuses {first_response.status_code}, {second_response.status_code}",
        )
        add_check(
            "created_record_has_id",
            created.get("id") == 1,
            f"Created ID {created.get('id')}",
        )

        title_search = client.get("/listings?search=sunny").json()
        add_check(
            "fastapi_search_property_title",
            len(title_search) == 1 and title_search[0]["id"] == 1,
            f"Matching IDs {[item['id'] for item in title_search]}",
        )

        location_search = client.get("/listings?search=oak").json()
        add_check(
            "fastapi_search_location",
            len(location_search) == 1 and location_search[0]["id"] == 2,
            f"Matching IDs {[item['id'] for item in location_search]}",
        )

        updated_listing = first_listing.copy()
        updated_listing["propertyTitle"] = "Updated Sunny Home"
        update_response = client.put("/listings/1", json=updated_listing)
        add_check(
            "fastapi_update_id_1",
            update_response.status_code == 200
            and update_response.json()["propertyTitle"]
            == "Updated Sunny Home",
            f"Status {update_response.status_code}",
        )

        delete_response = client.delete("/listings/2")
        remaining = client.get("/listings").json()
        add_check(
            "fastapi_delete_listing",
            delete_response.status_code == 200
            and [item["id"] for item in remaining] == [1],
            f"Remaining IDs {[item['id'] for item in remaining]}",
        )

    api_module.listings.clear()
    api_module.next_id = 1
except Exception as error:
    add_check("fastapi_import", False, str(error))
    for name in [
        "fastapi_get_listings",
        "fastapi_post_listing",
        "created_record_has_id",
        "fastapi_search_property_title",
        "fastapi_search_location",
        "fastapi_update_id_1",
        "fastapi_delete_listing",
    ]:
        if name not in checks:
            add_check(name, False, str(error))


try:
    import agent_graph

    add_check("langgraph_import_compile", agent_graph.graph is not None)

    original_complete = agent_graph.model_client.complete

    def valid_complete(messages, tools=None, temperature=None, json_output=False):
        prompt = messages[0]["content"]
        if "You are a reviewer." in prompt:
            output = {
                "tags": ["Rental", "Parking", "San Jose"],
                "summary": "A valid rental listing summary.",
                "changed": False,
                "reason": "",
            }
        else:
            output = {
                "tags": ["Rental", "Parking", "San Jose"],
                "summary": "A valid rental listing summary.",
            }
        return {
            "message": json.dumps(output),
            "input_tokens": 0,
            "output_tokens": 0,
        }

    graph_state = {
        "title": "Verification Rental",
        "content": "Rental listing used for the controlled graph smoke test.",
        "email": "verify@example.com",
        "strict": False,
        "task": "Generate rental listing tags and summary",
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "planner_attempts": 0,
        "turn_ceiling": 2,
        "validation_error": "",
        "validation_errors": [],
        "status": "running",
    }

    agent_graph.model_client.complete = valid_complete
    graph_result = agent_graph.graph.invoke(
        graph_state,
        {"recursion_limit": 20},
    )
    final_output = graph_result["reviewer_feedback"]
    tags = final_output.get("tags", [])
    summary = final_output.get("summary", "")
    schema_valid = (
        len(tags) == 3
        and all(isinstance(tag, str) for tag in tags)
        and all(3 <= len(tag) <= 30 for tag in tags)
        and len(summary.split()) <= 25
    )
    add_check(
        "graph_smoke_test",
        graph_result["status"] == "completed",
        f"Status {graph_result['status']}",
    )
    add_check(
        "graph_output_schema",
        schema_valid,
        f"Tags {tags}, summary words {len(summary.split())}",
    )

    required_state_fields = {
        "planner_attempts",
        "turn_ceiling",
        "status",
    }
    state_fields = set(agent_graph.AgentState.__annotations__)
    add_check(
        "loop_safety_fields",
        required_state_fields.issubset(state_fields),
        f"Fields {sorted(required_state_fields)}",
    )

    def invalid_complete(
        messages,
        tools=None,
        temperature=None,
        json_output=False,
    ):
        output = {
            "tags": ["X"],
            "summary": "Invalid tag count.",
        }
        return {
            "message": json.dumps(output),
            "input_tokens": 0,
            "output_tokens": 0,
        }

    agent_graph.model_client.complete = invalid_complete
    abandoned_result = agent_graph.graph.invoke(
        graph_state,
        {"recursion_limit": 20},
    )
    add_check(
        "loop_safety_abandoned",
        abandoned_result["status"] == "abandoned"
        and abandoned_result["planner_attempts"] == 2,
        (
            f"Status {abandoned_result['status']}, "
            f"attempts {abandoned_result['planner_attempts']}"
        ),
    )

    def rejected_complete(
        messages,
        tools=None,
        temperature=None,
        json_output=False,
    ):
        prompt = messages[0]["content"]
        if "You are a reviewer." in prompt:
            output = {
                "tags": ["Rental", "Parking", "San Jose"],
                "summary": "A valid rental listing summary.",
                "changed": True,
                "reason": "Use more specific tags.",
            }
        else:
            output = {
                "tags": ["Rental", "Parking", "San Jose"],
                "summary": "A valid rental listing summary.",
            }
        return {
            "message": json.dumps(output),
            "input_tokens": 0,
            "output_tokens": 0,
        }

    agent_graph.model_client.complete = rejected_complete
    rejected_result = agent_graph.graph.invoke(
        graph_state,
        {"recursion_limit": 20},
    )
    add_check(
        "reviewer_rejection_at_ceiling",
        rejected_result["status"] == "abandoned"
        and rejected_result["planner_attempts"] == 2,
        (
            f"Status {rejected_result['status']}, "
            f"attempts {rejected_result['planner_attempts']}"
        ),
    )

    agent_graph.model_client.complete = original_complete
except Exception as error:
    if "agent_graph" in locals() and "original_complete" in locals():
        agent_graph.model_client.complete = original_complete
    for name in [
        "langgraph_import_compile",
        "graph_smoke_test",
        "graph_output_schema",
        "loop_safety_fields",
        "loop_safety_abandoned",
        "reviewer_rejection_at_ceiling",
    ]:
        if name not in checks:
            add_check(name, False, str(error))


raw_files = {
    "schema_validation_runs": (
        reports_path / "raw/schema_validation_runs.json",
        30,
    ),
    "ceiling_2_runs": (
        reports_path / "raw/ceiling_2_runs.json",
        20,
    ),
    "ceiling_10_runs": (
        reports_path / "raw/ceiling_10_runs.json",
        20,
    ),
    "adversarial_runs": (
        reports_path / "raw/adversarial_runs.json",
        5,
    ),
}
counts_valid = True
json_valid = True
count_details = {}

for name, (path, expected_count) in raw_files.items():
    try:
        records = json.loads(path.read_text())
        count_details[name] = len(records)
        if len(records) != expected_count:
            counts_valid = False
    except (OSError, json.JSONDecodeError) as error:
        json_valid = False
        counts_valid = False
        count_details[name] = str(error)

add_check("raw_experiment_json_valid", json_valid, str(count_details))
add_check("experiment_output_counts", counts_valid, str(count_details))

metrics_path = reports_path / "METRICS.md"
metrics_nonempty = metrics_path.exists() and bool(
    metrics_path.read_text().strip()
)
add_check("metrics_nonempty", metrics_nonempty)

ai_use_path = reports_path / "AI_USE.md"
ai_text = ai_use_path.read_text() if ai_use_path.exists() else ""

ai_sections = [
    "## 1.",
    "## 2.",
    "## 3.",
    "## 4.",
]

ai_complete = (
    all(section in ai_text for section in ai_sections)
    and "[Answer later]" not in ai_text
)

missing_sections = [
    section for section in ai_sections
    if section not in ai_text
]

if ai_complete:
    ai_detail = "All four AI-use answers are present"
elif "[Answer later]" in ai_text:
    ai_detail = "AI_USE.md still contains [Answer later] placeholders"
else:
    ai_detail = f"Missing sections: {missing_sections}"

add_check("ai_use_complete", ai_complete, ai_detail)

run_log_path = reports_path / "RUN_LOG.txt"
run_log_text = run_log_path.read_text() if run_log_path.exists() else ""
run_log_valid = (
    "PART 4 - OUTPUT SCHEMA AND LOOP SAFETY" in run_log_text
    and "Command: python3.11 part4_experiment.py" in run_log_text
    and "Model: llama3.2:latest" in run_log_text
)
add_check("run_log_part4", run_log_valid)

screenshots = [
    "part1_375px.png",
    "part1_loading.png",
    "part1_empty.png",
    "part1_error.png",
    "part2_create.png",
    "part2_update_id1.png",
    "part2_search_title.png",
    "part2_search_location.png",
    "part2_before_delete.png",
    "part2_after_delete.png",
    "part3_normal_stream.png",
    "part3_correction_loop.png",
    "part4_validation_ceiling.png",
    "part4_metrics.png",
]
missing_screenshots = [
    name
    for name in screenshots
    if not (reports_path / "screenshots" / name).exists()
]
add_check(
    "required_screenshots",
    not missing_screenshots,
    (
        "All required screenshots exist"
        if not missing_screenshots
        else str(missing_screenshots)
    ),
)

commit_hash = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    text=True,
).strip()
working_tree_dirty = bool(
    subprocess.check_output(
        ["git", "status", "--porcelain"],
        text=True,
    ).strip()
)

result = {
    "homework": 2,
    "SID4": SID4,
    "commit_hash": commit_hash,
    "working_tree_dirty": working_tree_dirty,
    "working_tree_note": (
        "Verification ran on a working tree with uncommitted changes"
        if working_tree_dirty
        else "Verification ran on a clean working tree"
    ),
    "model": MODEL,
    "configuration": {
        "PORT_BASE": PORT_BASE,
        "PREFIX": PREFIX,
        "SEED": SEED,
        "VERIFY_SEED": VERIFY_SEED,
        "DOMAIN_ID": DOMAIN_ID,
    },
    "verification_timestamp": datetime.now().astimezone().isoformat(
        timespec="seconds"
    ),
    "checks": checks,
    "overall": (
        "PASS"
        if all(check["passed"] for check in checks.values())
        else "FAIL"
    ),
    "overall_passed": all(
        check["passed"] for check in checks.values()
    ),
}

reports_path.mkdir(parents=True, exist_ok=True)
with open(verification_path, "w") as file:
    json.dump(result, file, indent=2)

print(json.dumps(result, indent=2))
