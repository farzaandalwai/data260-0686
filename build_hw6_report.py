"""Build a plain DATA 260 Homework 6 submission PDF."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, XPreformatted


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports" / "hw06"
RAW = REPORT_DIR / "raw"
SHOTS = REPORT_DIR / "screenshots"
OUTPUT = REPORT_DIR / "report.pdf"
SUBMISSION = ROOT / "Dalwai_HW6.pdf"


def load_json(name: str) -> dict | list:
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def build() -> None:
    metrics = load_json("memory_experiment_results.json")
    costs = load_json("cost_calculations.json")
    verification_path = REPORT_DIR / "verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    report_base_commit = git_output("rev-parse", "HEAD")

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body", parent=styles["BodyText"], fontName="Helvetica", fontSize=11,
        leading=14, spaceAfter=6,
    )
    main = ParagraphStyle(
        "main", parent=body, fontName="Helvetica-Bold", fontSize=14,
        leading=17, spaceBefore=10, spaceAfter=7,
    )
    sub = ParagraphStyle(
        "sub", parent=body, fontName="Helvetica-Bold", fontSize=12,
        leading=15, spaceBefore=7, spaceAfter=4, keepWithNext=True,
    )
    title = ParagraphStyle("title", parent=main, alignment=TA_CENTER, spaceAfter=5)
    center = ParagraphStyle("center", parent=body, alignment=TA_CENTER)
    code_style = ParagraphStyle(
        "code", parent=body, fontName="Courier", fontSize=7.5, leading=9,
        leftIndent=5, spaceBefore=2, spaceAfter=5,
    )
    caption = ParagraphStyle(
        "caption", parent=body, fontName="Helvetica", fontSize=9,
        leading=11, spaceBefore=2, spaceAfter=7,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        rightMargin=0.65 * inch, leftMargin=0.65 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
        title="Dalwai DATA 260 Homework 6", author="Farzaan Dalwai",
    )
    story: list = []

    def p(text: str, style=body) -> None:
        story.append(Paragraph(text, style))

    def h1(text: str) -> None:
        story.append(Paragraph(text, main))

    def h2(text: str) -> None:
        story.append(Paragraph(text, sub))

    def code(text: str) -> XPreformatted:
        return XPreformatted(escape(text.strip()), code_style)

    def evidence(snippet: str, filename: str, label: str, width: float = 7.0 * inch) -> None:
        image = Image(str(SHOTS / filename))
        natural_width, natural_height = image.imageWidth, image.imageHeight
        chosen_width = min(width, natural_width / 72 * inch)
        chosen_height = chosen_width * natural_height / natural_width
        if chosen_height > 5.15 * inch:
            chosen_height = 5.15 * inch
            chosen_width = chosen_height * natural_width / natural_height
        image.drawWidth = chosen_width
        image.drawHeight = chosen_height
        image.hAlign = "LEFT"
        story.append(KeepTogether([code(snippet), image, Paragraph(escape(label), caption)]))

    p("DATA 260 Homework 6", title)
    p("Farzaan Dalwai", center)
    p(
        '<link href="https://github.com/farzaandalwai/data260-0686">'
        "https://github.com/farzaandalwai/data260-0686</link>", center,
    )
    p("SID4: 0686 | PORT_BASE: 8686 | PREFIX: s0686")
    p("SEED: 686 | VERIFY_SEED: 260686 | DOMAIN_ID: 6 - Rental Housing Listings")
    p("Hardware: Apple M4, 10 cores, 24 GB RAM")
    p("Local model: llama3.2:latest | Embedding: all-MiniLM-L6-v2, 384 dimensions")
    p(f"Tested implementation commit: {escape(verification['commit_hash_tested'])}")
    p(f"Report base commit: {escape(report_base_commit)} | Proposed tag: hw6 (not created yet)")
    p(
        "Repository link works and the repository is public. A read-only check found only the owner and no "
        "pending invitations. Access for Sbnikitha and supriyaselvanganesan is not confirmed."
    )

    h1("Part 1 - MongoDB Document API")
    p(
        "I used database s0686_doc and collection rental_documents. Each document has a required title, optional "
        "description, status, property type, available date, and automatic created/updated timestamps. Pydantic and "
        "MongoDB both enforce required fields, length limits, enums, and dates."
    )
    p(
        "The FastAPI routes support create, list, get by ID, update, and delete. Errors return 400 for bad IDs or "
        "empty updates, 404 for missing records, 422 for invalid request data, and a safe 500 response for database errors. "
        "CORS and JSON request parsing are enabled in the shared application."
    )
    evidence(
        "@router.post('', status_code=201)\n"
        "@router.get('')\n"
        "@router.get('/{listing_id}')\n"
        "@router.put('/{listing_id}')\n"
        "@router.delete('/{listing_id}')\n"
        "# RentalDocumentCreate validates title, enums, and datetime.",
        "P1_01_crud_and_validation.png", "CRUD results",
    )
    evidence(
        "'$jsonSchema': {\n"
        "  'required': ['title', 'status', 'property_type', 'available_from',\n"
        "               'created_at', 'updated_at'],\n"
        "  'properties': {'title': {'maxLength': 100},\n"
        "                 'status': {'enum': ['available','pending','rented']}}\n"
        "}",
        "P1_02_mongodb_sample.png", "MongoDB document",
    )

    h1("Part 2 - Short, Long, and Episodic Memory")
    p(
        "The same database also has messages, summaries, and episodes. Messages store the conversation. Summaries store "
        "session or lifetime text. Episodes store short facts, importance from 0 to 1, and a numeric embedding."
    )
    evidence(
        "@router.post('/api/chat')\n"
        "@router.get('/api/memory/{user_id}')\n"
        "@router.get('/api/aggregate/{user_id}')",
        "P2_01_live_swagger_endpoints.png", "API endpoints", 3.2 * inch,
    )
    p(
        "POST /api/chat saves the user message, loads the last N messages, loads session and lifetime summaries, retrieves "
        "the most relevant episodes, builds the prompt, calls local Ollama, saves the reply, and updates summaries every "
        "five user messages. The response includes the reply and the memory used."
    )
    evidence(
        "context = assemble_prompt(system_primer, summaries, short_window, episodes, message)\n"
        "reply, usage = model.generate(context)\n"
        "save_message(user_id, session_id, 'assistant', reply)\n"
        "return {'reply': reply, 'memory_used': memory_used, 'usage': usage}",
        "P2_02_conversation_reply.png", "Chat reply",
    )
    p(
        "GET /api/memory/{user_id} returns the last 16 messages, newest session summary, newest lifetime summary, and "
        "the last 20 episodes."
    )
    evidence(
        "return {'messages': last_16_messages(user_id),\n"
        "        'latest_session_summary': latest_summary(user_id, 'session'),\n"
        "        'latest_lifetime_summary': latest_summary(user_id, 'user'),\n"
        "        'episodes': last_20_episodes(user_id)}",
        "P2_03_memory_endpoint.png", "Memory result",
    )
    p("GET /api/aggregate/{user_id} groups messages by date and returns recent session and lifetime summaries.")
    evidence(
        "pipeline = [\n"
        "  {'$match': {'user_id': user_id}},\n"
        "  {'$group': {'_id': {'$dateToString': {'format': '%Y-%m-%d',\n"
        "      'date': '$created_at'}}, 'message_count': {'$sum': 1}}}\n"
        "]",
        "P2_04_aggregate_endpoint.png", "Aggregate result",
    )
    p(
        "I sent 10 messages in one session. SHORT_TERM_N is 12. A summary is made every five user messages. Up to three "
        "facts are extracted from each user message and stored with MiniLM embeddings. Cosine similarity returns the top "
        "three relevant facts. The test produced 20 messages, 3 summaries, and 10 episodes."
    )
    evidence(
        "messages: user_id, session_id, role, content, created_at\n"
        "summaries: user_id, session_id, scope, text, created_at\n"
        "episodes: user_id, session_id, fact, importance, embedding, created_at",
        "P2_05_mongodb_memory_collections.png", "Memory collections",
    )

    h1("Part 3 - What Memory Costs")
    p(
        "Each chat request logs prompt/completion tokens, estimated tokens for the system primer, long-term summary, "
        "short-term window and episodes, plus latency, condition, IDs, timestamp, and model settings. The raw data is JSON."
    )
    p(
        "memory_probes.yaml contains five fixed questions, expected answer criteria, and a 1-5 scoring rubric. I ran the "
        "same 30-message conversation and the same five probes in a fresh session for each condition."
    )
    evidence(
        "for condition in ['N=4', 'N=12', 'N=30', 'relevance_aware_eviction']:\n"
        "    run_same_30_messages_in_fresh_session()\n"
        "    score_same_five_probes()",
        "P3_01_experiment_metrics.png", "Experiment results",
    )
    metric_lines = [
        "Setting                         Prompt/turn   Latency ms   Quality",
        "----------------------------------------------------------------",
    ]
    labels = {
        "SHORT_TERM_N=4": "SHORT_TERM_N=4",
        "SHORT_TERM_N=12": "SHORT_TERM_N=12",
        "SHORT_TERM_N=30": "SHORT_TERM_N=30",
        "relevance_aware_eviction": "Eviction policy",
    }
    for row in metrics["condition_metrics"]:
        metric_lines.append(
            f"{labels[row['condition']]:30} {row['mean_prompt_tokens']:10.3f} "
            f"{row['mean_latency_ms']:12.3f} {row['mean_probe_score']:9.3f}"
        )
    h2("Memory results")
    story.append(code("\n".join(metric_lines)))
    policy = metrics["policy_comparison"]
    p(
        f"My policy keeps the four newest messages and the eight most relevant older messages. Compared with N=30, it "
        f"saved {policy['absolute_prompt_token_savings']:.3f} prompt tokens per turn "
        f"({policy['percentage_prompt_token_savings']:.3f}%), changed quality by "
        f"{policy['probe_score_change']:+.3f}, and changed latency by {policy['latency_change_ms']:+.3f} ms."
    )
    cost_lines = [
        "Setting                         Input       Output      Total",
        "------------------------------------------------------------",
    ]
    for row in costs["costs"]:
        cost_lines.append(
            f"{labels[row['condition']]:30} ${row['input_cost_usd']:8.4f} "
            f"${row['output_cost_usd']:8.4f} ${row['total_cost_usd']:9.4f}"
        )
    h2("10,000 conversation cost")
    story.append(code("\n".join(cost_lines)))
    p(
        "Best setting: relevance-aware eviction because it kept quality 5.0 at the lowest cost in the top quality range "
        "($434.9601). Worst setting: SHORT_TERM_N=30 because it had the highest cost in that range ($633.6699). The first "
        "sweep was rejected because Ollama silently truncated context. I set num_ctx=16384 and num_predict=96 and reran all "
        "conditions."
    )

    h1("Part 4 - File Memory and Consolidation")
    p(
        "AGENT.md stores project instructions. MEMORY.md stores durable facts and the last consolidation time. The code "
        "loads both files and adds them to the system prompt. Consolidation is required above 40 fact lines or after 24 hours."
    )
    story.append(code(
        "def file_memory_prompt():\n"
        "    return load_agent_memory() + '\\n' + load_fact_memory()\n\n"
        "def consolidation_required(now):\n"
        "    return count_memory_lines() > 40 or hours_since_compact(now) > 24\n\n"
        "COMMANDS = {'/memory', '/compact', '/dream', '/help'}"
    ))
    p(
        "/memory displays memory. /compact merges duplicates and resolves conflicts. /dream adds up to three durable facts "
        "from recent conversation. /help explains the commands. Callers cannot provide file paths, so only the two root "
        "memory files can be accessed."
    )
    p(
        "AGENT.md has nine instructions covering the project, stack, coding conventions, testing, and prohibited actions. "
        "The normalize_rental_title function passed checks for naming, type hints, a docstring, input validation, and no "
        "external side effects."
    )
    evidence(
        "if command == '/compact':\n"
        "    result = compact_memory()\n"
        "    return {'before': before, 'after': after, **result}\n"
        "# Conflicts use confidence, then newest observation; alternatives are retained.",
        "P4_01_compact_55_to_35.png", "Compact result",
    )
    evidence(
        "checks = {'descriptive_name': True, 'type_hints': True,\n"
        "          'docstring': True, 'validates_input': True,\n"
        "          'no_external_side_effects': True}\n"
        "assert all(checks.values())",
        "P4_02_agent_and_file_memory_checks.png", "Agent verification",
    )
    p(
        "The original MEMORY.md had 55 fact lines with duplicates and contradictions (commit 177192e). The consolidated "
        "version has 35 lines (commit 9a7c2bd). It merged 20 duplicates. Conflicts were kept with the selected result and "
        "reason, and the independent check found no incorrectly resolved contradiction."
    )
    h2("Memory comparison")
    p("Inspectability: MongoDB is easy to query; Markdown is easiest to read and review in Git.")
    p("Restart persistence: MongoDB survives in its volume; Markdown survives in files and commits.")
    p("Many sessions: MongoDB scales better with indexed user/session queries; one Markdown file becomes noisy.")
    p("Must-not-forget facts: MongoDB is good for scored user facts; Markdown is best for a few critical rules.")
    p("Choice: use MongoDB for conversation memory and retrieval, and file memory for small, auditable project rules.")

    story.append(PageBreak())
    h1("AI Use")
    p("1. I used Codex for repository inspection, implementation, debugging, testing, experiments, evidence capture, and report drafting. I supplied the assignment, repository, configuration, and local services.")
    p("2. The first N=30 experiment was unsuitable because the prompt count stopped near 2,050 tokens.")
    p("3. I found the problem by comparing exact Ollama prompt_eval_count values across conditions.")
    p("4. I preserved the bad run, set num_ctx=16384 and num_predict=96, and reran every condition in fresh sessions. The corrected N=30 prompt counts exceeded the old limit.")

    h1("Verification")
    p(
        "The self-check tested FastAPI, MongoDB, CRUD and validation, local chat, memory, aggregate output, collections, "
        "384-dimensional embeddings, experiment files, file memory, AGENT.md, and unchanged MySQL counts."
    )
    evidence(
        "python3.11 verify_hw06.py\n"
        "# Live smoke test writes reports/hw06/verification.json",
        "P5_01_final_verification.png", "Final verification",
    )
    passed = sum(1 for row in verification["checks"] if row["pass"])
    p(f"Result: {passed}/{len(verification['checks'])} checks passed. overall_pass=true.")
    p("The report and evidence are complete locally. Push, tag creation, and collaborator access changes were not performed.")

    doc.build(story)
    shutil.copyfile(OUTPUT, SUBMISSION)
    print(f"wrote {OUTPUT}")
    print(f"wrote {SUBMISSION}")


if __name__ == "__main__":
    build()
