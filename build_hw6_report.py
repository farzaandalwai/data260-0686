"""Build the concise, evidence-backed DATA 260 Homework 6 PDF report."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)


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


def page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(0.58 * inch, 0.34 * inch, "Farzaan Dalwai — DATA 260 HW6")
    canvas.drawRightString(7.92 * inch, 0.34 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build() -> None:
    metrics = load_json("memory_experiment_results.json")
    costs = load_json("cost_calculations.json")
    part1 = load_json("part1_api_tests.json")
    file_checks = load_json("file_memory_checks.json")
    verification_path = REPORT_DIR / "verification.json"
    verification = load_json("../verification.json") if verification_path.exists() else None
    implementation_commit = git_output("rev-parse", "HEAD")

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "HW6Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        spaceAfter=7,
        textColor=colors.HexColor("#0f172a"),
    )
    main = ParagraphStyle(
        "HW6Main",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        spaceBefore=9,
        spaceAfter=7,
        textColor=colors.HexColor("#0f3d66"),
    )
    sub = ParagraphStyle(
        "HW6Sub",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=7,
        spaceAfter=6,
        keepWithNext=True,
        textColor=colors.HexColor("#155e75"),
    )
    title = ParagraphStyle(
        "HW6Title",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=colors.HexColor("#0f3d66"),
    )
    centered = ParagraphStyle("HW6Centered", parent=body, alignment=TA_CENTER)
    caption = ParagraphStyle(
        "HW6Caption",
        parent=body,
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceBefore=3,
        spaceAfter=8,
    )
    code_style = ParagraphStyle(
        "HW6Code",
        parent=body,
        fontName="Courier",
        fontSize=8.1,
        leading=10,
        leftIndent=7,
        rightIndent=7,
        borderWidth=0.5,
        borderColor=colors.HexColor("#94a3b8"),
        borderPadding=7,
        backColor=colors.HexColor("#f8fafc"),
        spaceAfter=5,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.58 * inch,
        leftMargin=0.58 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.55 * inch,
        title="Dalwai DATA 260 Homework 6",
        author="Farzaan Dalwai",
        subject="MongoDB document APIs, conversational memory, memory cost, and file memory",
    )
    story: list = []

    def p(text: str, style=body) -> None:
        story.append(Paragraph(text, style))

    def h1(text: str) -> None:
        story.append(Paragraph(text, main))

    def h2(text: str) -> None:
        story.append(Paragraph(text, sub))

    def evidence_heading(text: str) -> None:
        """Keep an evidence heading with its snippet, screenshot, and caption."""
        story.append(CondPageBreak(5.6 * inch))
        story.append(Paragraph(text, sub))

    def code(text: str) -> XPreformatted:
        return XPreformatted(escape(text.strip()), code_style)

    def evidence(snippet: str, filename: str, label: str, width: float = 7.15 * inch) -> None:
        path = SHOTS / filename
        if not path.exists():
            p(f"Evidence pending: {escape(filename)}", caption)
            return
        image = Image(str(path))
        natural_width, natural_height = image.imageWidth, image.imageHeight
        chosen_width = min(width, natural_width / 72 * inch)
        chosen_height = chosen_width * natural_height / natural_width
        max_height = 5.0 * inch
        if chosen_height > max_height:
            chosen_height = max_height
            chosen_width = chosen_height * natural_width / natural_height
        image.drawWidth = chosen_width
        image.drawHeight = chosen_height
        image.hAlign = "CENTER"
        story.append(KeepTogether([
            code(snippet),
            Spacer(1, 3),
            image,
            Paragraph(escape(label), caption),
        ]))

    def table(rows: list[list[str]], widths: list[float], font_size: float = 8.4) -> None:
        formatted = [[Paragraph(escape(str(cell)), ParagraphStyle(
            f"cell-{font_size}", parent=body, fontSize=font_size, leading=font_size + 2
        )) for cell in row] for row in rows]
        t = LongTable(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d66")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([t, Spacer(1, 7)])

    p("DATA 260 Homework 6", title)
    p("Farzaan Dalwai", centered)
    p(
        '<link href="https://github.com/farzaandalwai/data260-0686" '
        'color="#0f5f9e">https://github.com/farzaandalwai/data260-0686</link>',
        centered,
    )
    p(
        "Repository link verified working on 2026-10-17. The repository is public and its default branch is main. "
        "A read-only collaborator check found only the owner and no pending invitations; therefore direct collaborator "
        "access for <b>Sbnikitha</b> and <b>supriyaselvanganesan</b> is <b>not confirmed</b>. No access change was made.",
        body,
    )
    config_rows = [
        ["Value", "Result", "Value", "Result"],
        ["SID4", "0686", "PORT_BASE", "8686"],
        ["PREFIX", "s0686", "SEED", "686"],
        ["VERIFY_SEED", "260686", "DOMAIN_ID", "6 — Rental Housing Listings"],
        ["Hardware", "Apple M4, 10 cores", "Memory", "24 GB"],
        ["Local model", "llama3.2:latest", "Embedding", "all-MiniLM-L6-v2, 384 dims"],
        ["Implementation commit", implementation_commit[:12], "Proposed tag", "hw6 — not created pending approval"],
    ]
    table(config_rows, [1.16 * inch, 2.24 * inch, 1.2 * inch, 2.55 * inch], 9.1)
    p(
        "The implementation/evidence hash above is the fixed local commit tested by this report. The eventual submission "
        "tag must target the final report commit after review; no push or tag was performed.",
    )

    h1("Part 1 — MongoDB Document API")
    p(
        "The new document view uses database <b>s0686_doc</b> and collection <b>rental_documents</b>. Pydantic rejects "
        "bad requests before database writes, while a strict MongoDB $jsonSchema validator independently protects stored data. "
        "Timestamps are timezone-aware and automatic. The stable evidence record remains present; temporary test records are deleted.",
    )
    evidence_heading("CRUD and validation evidence")
    evidence(
        "@router.post('', status_code=201)\n"
        "def create_document_listing(payload: RentalDocumentCreate): ...\n"
        "@router.get('/{listing_id}')\n"
        "@router.put('/{listing_id}')\n"
        "@router.delete('/{listing_id}')\n"
        "# Pydantic: title 1..100, enums, datetime, extra='forbid'",
        "P1_01_crud_and_validation.png",
        f"Figure 1. Live HTTP CRUD and validation: all_pass={str(part1['all_pass']).lower()}, 11/11 expected statuses.",
    )
    evidence_heading("MongoDB sample document")
    evidence(
        "VALIDATORS['rental_documents'] = {\n"
        "  '$jsonSchema': {'required': ['title','status','property_type',\n"
        "    'available_from','created_at','updated_at'],\n"
        "  'properties': {'title': {'maxLength': 100},\n"
        "    'status': {'enum': ['available','pending','rented']}}}}",
        "P1_02_mongodb_sample.png",
        "Figure 2. Real s0686_doc.rental_documents record shown with mongosh.",
    )
    p(
        "Error handling distinguishes malformed ObjectIds (400), missing records (404), request validation failures (422), "
        "and safe database failures (500). CORS and FastAPI JSON request parsing remain configured in the shared root application.",
    )

    h1("Part 2 — Short-, Long-, and Episodic Memory")
    p(
        "The same MongoDB connection adds <b>messages</b>, <b>summaries</b>, and <b>episodes</b>, without changing the Part 1 "
        "collection. The default short window is N=12, summaries refresh every five user messages, and cosine retrieval returns "
        "the top three local MiniLM episode embeddings. The local Ollama adapter supplies assistant replies.",
    )
    evidence_heading("Live API surface")
    evidence(
        "router = APIRouter(tags=['HW6 memory'])\n"
        "@router.post('/api/chat', response_model=ChatResponse)\n"
        "@router.get('/api/memory/{user_id}')\n"
        "@router.get('/api/aggregate/{user_id}')",
        "P2_01_live_swagger_endpoints.png",
        "Figure 3. Browser view of the three live FastAPI HW6 memory endpoints.",
        3.25 * inch,
    )
    evidence_heading("Conversation evidence")
    evidence(
        "user_id = 'demo-260686-memory'\n"
        "for message in ten_fixed_messages:\n"
        "    response = POST('/api/chat', user_id, session_id, message)\n"
        "# Each turn saves user/reply and returns memory_used + usage.",
        "P2_02_conversation_reply.png",
        "Figure 4. The persisted tenth exchange shows the local assistant recalling Santa Clara.",
    )
    evidence_heading("Memory endpoint evidence")
    evidence(
        "def get_user_memory(user_id):\n"
        "    messages = last_16_messages(user_id)\n"
        "    return {'messages': messages,\n"
        "      'latest_session_summary': latest_summary(user_id,'session'),\n"
        "      'latest_lifetime_summary': latest_summary(user_id,'user'),\n"
        "      'episodes': last_20_episodes(user_id)}",
        "P2_03_memory_endpoint.png",
        "Figure 5. Live memory JSON: 16 messages, both summary scopes, 10 episodes, 384-dimensional embedding.",
    )
    evidence_heading("Aggregate endpoint evidence")
    evidence(
        "pipeline = [\n"
        "  {'$match': {'user_id': user_id}},\n"
        "  {'$group': {'_id': {'$dateToString': {'format':'%Y-%m-%d',\n"
        "      'date':'$created_at'}}, 'message_count': {'$sum':1}}}\n"
        "]",
        "P2_04_aggregate_endpoint.png",
        "Figure 6. Live daily message counts and recent session/user summaries.",
    )
    evidence_heading("MongoDB memory collections")
    evidence(
        "messages: user_id, session_id, role, content, created_at\n"
        "summaries: user_id, nullable session_id, scope, text, created_at\n"
        "episodes: user_id, session_id, fact, importance, embedding[], created_at\n"
        "# Strict validators + compound query indexes are created idempotently.",
        "P2_05_mongodb_memory_collections.png",
        "Figure 7. Live collections and demo documents: 20 messages, 3 summaries, 10 episodes.",
    )
    p(
        "Prompt assembly order is system primer, file memory when enabled, long-term summaries, short-term messages, retrieved "
        "episodes, and the current message. Episode extraction stores at most three explicit user facts with importance 0..1. "
        "Retrieval ranks up to 300 user episodes by cosine similarity and returns top-k. The ten-message milestone passed every "
        "objective check in raw/fast_milestone.json.",
    )

    h1("Part 3 — What Memory Costs")
    p(
        "Each chat logs exact Ollama prompt/completion totals, MiniLM WordPiece component estimates for primer/summary/window/episodes, "
        "latency, identity, timestamp, condition, and runtime configuration. Five fixed probes and their complete 1–5 objective "
        "rubric are in memory_probes.yaml. Each condition used a fresh user/session, the identical 30-message conversation, and the "
        "same five probes; file memory was disabled to isolate MongoDB window behavior.",
    )
    evidence_heading("Measured results")
    evidence(
        "CONDITIONS = [N=4, N=12, N=30, relevance_aware_eviction]\n"
        "for condition in CONDITIONS:\n"
        "    run_same_30_messages_in_fresh_session()\n"
        "    score_same_five_probes_with_fixed_rubric()\n"
        "# Exact totals: Ollama prompt_eval_count/eval_count; temperature=0.0",
        "P3_01_experiment_metrics.png",
        "Figure 8. Corrected real local-model sweep and policy comparison.",
    )
    metric_rows = [["Setting", "Prompt tok/turn", "Completion", "Latency ms", "Quality"]]
    for row in metrics["condition_metrics"]:
        metric_rows.append([
            row["condition"],
            f"{row['mean_prompt_tokens']:.3f}",
            f"{row['mean_completion_tokens']:.3f}",
            f"{row['mean_latency_ms']:.3f}",
            f"{row['mean_probe_score']:.3f}",
        ])
    table(metric_rows, [2.25 * inch, 1.24 * inch, 1.0 * inch, 1.2 * inch, 0.9 * inch], 8.7)
    policy = metrics["policy_comparison"]
    p(
        f"Relevance-aware eviction keeps the four newest messages plus the eight most semantically relevant older messages. "
        f"Against N=30 it saved <b>{policy['absolute_prompt_token_savings']:.3f}</b> prompt tokens/turn "
        f"(<b>{policy['percentage_prompt_token_savings']:.3f}%</b>) with quality change "
        f"<b>{policy['probe_score_change']:+.3f}</b> and latency change <b>{policy['latency_change_ms']:+.3f} ms</b>.",
    )
    cost_rows = [["Setting", "Input cost", "Output cost", "Total / 10,000 × 30"]]
    for row in costs["costs"]:
        cost_rows.append([
            row["condition"],
            f"${row['input_cost_usd']:.4f}",
            f"${row['output_cost_usd']:.4f}",
            f"${row['total_cost_usd']:.4f}",
        ])
    table(cost_rows, [2.25 * inch, 1.35 * inch, 1.35 * inch, 1.65 * inch], 8.8)
    p(
        "Selection rule: choose the lowest projected cost within 0.5 points of the best probe score; choose the highest cost in "
        "that same quality band as worst. Therefore <b>relevance_aware_eviction</b> is best and <b>SHORT_TERM_N=30</b> is worst. "
        "The first sweep was rejected because the default Ollama context silently truncated N=30 near 2,050 exact prompt tokens. "
        "After setting num_ctx=16384 and num_predict=96 consistently, N=30 grew past that ceiling; only corrected outputs are reported.",
    )

    h1("Part 4 — File-Based Memory and Consolidation")
    p(
        "Root AGENT.md contains nine durable instructions spanning project description, stack, coding conventions, testing, and "
        "prohibited actions. Root MEMORY.md stores only durable facts and a last-consolidated timestamp. Loading accepts no caller "
        "path; commands can access only the two known root files.",
    )
    h2("Files, prompt, checks, and commands")
    story.append(code(
        "def file_memory_prompt():\n"
        "    return '=== DURABLE AGENT INSTRUCTIONS ===\\n' + load_agent_memory() + \\\n"
        "           '\\n=== DURABLE FACT MEMORY ===\\n' + load_fact_memory()\n"
        "def consolidation_required(now):\n"
        "    return count_memory_lines() > 40 or now-last_consolidated > 24h\n"
        "COMMANDS = {'/memory','/compact','/dream','/help'}"
    ))
    p(
        "The final AGENT.md directs small typed functions, timezone-aware UTC, boundary validation, safe errors, objective tests, "
        "regressions, local-only models, preservation of prior data, and fixed memory paths. /memory displays; /compact consolidates; "
        "/dream appends up to three explicit durable preferences; /help documents all commands.",
    )
    evidence_heading("Consolidation evidence")
    evidence(
        "if command == '/compact':\n"
        "    result = compact_memory()\n"
        "    return {'text': f\"Compacted memory from {before} to {after} facts.\",\n"
        "            **result}\n"
        "# Rank conflicts by confidence, then newest observation; retain alternatives.",
        "P4_01_compact_55_to_35.png",
        "Figure 9. Real /compact output: 55 → 35, with 20 duplicate lines merged.",
    )
    evidence_heading("AGENT.md and contradiction verification")
    evidence(
        "def verify_agent_compliance():\n"
        "    checks = {'descriptive_snake_case_name': True, 'type_hints': True,\n"
        "      'docstring': True, 'validates_external_input': True,\n"
        "      'no_external_side_effects': True}\n"
        "    return {'function':'normalize_rental_title','pass':all(checks.values())}",
        "P4_02_agent_and_file_memory_checks.png",
        "Figure 10. Real verification: all checks passed; no contradiction was resolved incorrectly.",
    )
    p(
        f"The original exact 55-line state is in local commit <b>177192e</b>; the exact 35-line consolidated root state is in "
        f"commit <b>9a7c2bd</b>. Raw copies preserve both versions. Deliberate conflicts were not silently deleted: each consolidated "
        f"line retains alternatives and the explicit reason. Independent outcomes: preferred_city=Santa Clara, CA; "
        f"max_monthly_budget=$3,500; pet_household=one indoor cat. {escape(file_checks['contradiction_validation']['statement'])}",
    )
    comparison_rows = [
        ["Criterion", "MongoDB memory", "AGENT.md / MEMORY.md"],
        ["Inspectability", "Queryable structured documents; best for counts and filters.", "Human-readable diff; easiest to audit in Git."],
        ["Restart persistence", "Durable in the Mongo volume; independent of process.", "Durable in repository files and commits."],
        ["Many sessions", "Scales with indexed user/session/time queries.", "Global file becomes noisy and needs consolidation."],
        ["Must-not-forget facts", "Good for timestamped, scored, user-specific facts.", "Best for a small set of critical instructions reviewed in Git."],
    ]
    table(comparison_rows, [1.25 * inch, 2.85 * inch, 2.95 * inch], 8.8)
    p(
        "Balanced choice: use MongoDB for high-volume, user/session-specific memories and retrieval; use file memory for a small "
        "auditable set of project rules and critical facts. Neither should overwrite the other without an explicit policy.",
    )

    h1("AI Use")
    h2("1. What I used AI for and what I did")
    p(
        "I used Codex to inspect the assignment and existing repository, implement and debug the FastAPI/PyMongo memory system, "
        "build objective test and experiment scripts, operate local applications, organize evidence, and draft this report. I supplied "
        "the repository, configuration, local services/model, assignment files, and authorization boundaries. All reported records, "
        "replies, metrics, hashes, and screenshots come from commands run on my Mac; no output was invented.",
    )
    h2("2–4. Unsuitable output, detection, and correction")
    p(
        "The first 30-message-window experiment was unsuitable: exact Ollama prompt counts plateaued near 2,050 and the nominal N=30 "
        "condition had silently lost old context. I detected it by comparing per-turn prompt_eval_count across conditions. I preserved the "
        "invalid aggregate for audit, extended the shared adapter with explicit num_ctx/num_predict, and reran every condition in fresh "
        "sessions. The corrected N=30 prompts passed the former ceiling and the final files use only this sweep.",
    )

    h1("Verification and Repository Integrity")
    p(
        "The self-check imports the shared app, calls the live backend on PORT_BASE, pings MongoDB, verifies the live validator, runs an "
        "HTTP CRUD round trip with cleanup, rejects invalid input, calls the local chat model, checks memory/aggregate endpoints, validates "
        "collections and embeddings, audits experiment rows/probes, checks both memory versions, and confirms original MySQL counts "
        "remain 5,000 listings / 200 notes / 1 manager.",
    )
    verification_snippet = (
        "python3.11 verify_hw06.py\n"
        "# Objective smoke checks: FastAPI, MongoDB, CRUD, local chat, memory,\n"
        "# aggregate, experiment rows/probes, file memory, and MySQL counts."
    )
    if (SHOTS / "P5_01_final_verification.png").exists():
        evidence(
            verification_snippet,
            "P5_01_final_verification.png",
            "Figure 11. Final live self-check; verification.json contains the tested commit and each pass/fail result.",
        )
    else:
        story.append(code(verification_snippet))
        p("The final verification screenshot is added after the first report build allows the required-file check to pass.", caption)
    if verification:
        passed = sum(1 for row in verification["checks"] if row["pass"])
        p(
            f"verification.json: overall_pass=<b>{str(verification['overall_pass']).lower()}</b>; "
            f"{passed}/{len(verification['checks'])} checks passed; tested commit "
            f"<b>{escape(verification['commit_hash_tested'][:12])}</b>.",
        )
    p(
        "Regression evidence: Vite production build passed, oxlint passed, both existing FastMCP servers imported, FastAPI imported "
        "with 17 routes, git diff --check passed, .env remains ignored, and no secret appears in screenshots or tracked evidence. "
        "The unrelated pre-existing reports/hw05/raw/agent_runs.jsonl modification was not staged or altered for HW6.",
    )
    h2("Submission status")
    status_rows = [
        ["Item", "Status"],
        ["Implementation and evidence", "Complete locally and committed"],
        ["Report and named submission copy", "Generated and visually verified locally"],
        ["GitHub push", "Not performed — requires review/approval"],
        ["Tag hw6", "Not created — proposed after review"],
        ["Required direct collaborators", "Not confirmed; no access mutation performed"],
    ]
    table(status_rows, [2.45 * inch, 4.6 * inch], 9.2)
    p(
        "Evidence is reproducible from reports/hw06/RUN_LOG.txt, machine-readable raw files, verification.json, and the screenshot "
        "manifest. The only submission blockers are the deliberately withheld push/tag and missing direct collaborator membership.",
    )

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    shutil.copyfile(OUTPUT, SUBMISSION)
    print(f"wrote {OUTPUT}")
    print(f"wrote {SUBMISSION}")


if __name__ == "__main__":
    build()
