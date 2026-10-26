import io
import json
from html import escape
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer


ROOT = Path("reports/hw07")
SHOTS = ROOT / "screenshots"
OUTPUT = ROOT / "Dalwai_HW7.pdf"
PAGE = landscape(A4)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=14, spaceAfter=5)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=14, leading=17, spaceAfter=8)
PART = ParagraphStyle("part", parent=BODY, fontName="Helvetica-Bold", fontSize=14, leading=17, spaceBefore=14, spaceAfter=7)
SUB = ParagraphStyle("sub", parent=BODY, fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=8, spaceAfter=4)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.5, leading=10, textColor=colors.black, leftIndent=8, spaceAfter=5)


def paragraph(text, style=BODY):
    return Paragraph(escape(text), style)


def screenshot(name, max_width=690, max_height=375):
    source = PILImage.open(SHOTS / name)
    if name.endswith(".png"):
        bottoms = {
            "01_ruff_failure.png": 1370,
            "02_ruff_success.png": 560,
            "07_auth_statuses.png": 660,
            "08_agent_tasks.png": 930,
            "08b_reliability.png": 560,
            "09_reflexion.png": 880,
            "10_injection_matrix.png": 760,
            "11_sandbox.png": 580,
            "12_verification.png": 570,
            "13_commit_hook.png": 750,
        }
        left, top, right, bottom = (760, 180, 2700, bottoms[name])
        source = source.crop((left, top, right, bottom))
    elif name in {"03_bike_member_ui.jpg", "05_bike_sparse_ui.jpg"}:
        source = source.crop((165, 90, 1180, 820))
    elif name == "04_bike_member_timeline.jpg":
        source = source.crop((170, 0, 1180, 750))
    buffer = io.BytesIO()
    source.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    width, height = source.size
    factor = min(max_width / width, max_height / height)
    image = Image(buffer, width=width * factor, height=height * factor)
    image.hAlign = "LEFT"
    return image


def evidence(story, heading, sentence, snippet, image, max_height=375):
    block = [paragraph(heading, SUB), paragraph(sentence), Preformatted(snippet, CODE), screenshot(image, max_height=max_height), Spacer(1, 9)]
    story.append(KeepTogether(block))


def main():
    verification = json.loads((ROOT / "verification.json").read_text())
    story = [
        paragraph("DATA 260 Homework 7 — Farzaan Dalwai", TITLE),
        paragraph("Repository: https://github.com/farzaandalwai/data260-0686"),
        paragraph("SID4 0686  |  PORT_BASE 8686  |  PREFIX s0686  |  SEED 686  |  VERIFY_SEED 260686  |  DOMAIN_ID 6"),
        paragraph("Rental-housing domain; MySQL s0686_rel; FastAPI 8686; React 5173; Python 3.11.14; macOS 26.6.2 arm64; local model llama3.2:latest."),
        paragraph("Implementation commit 0f36332004971170feeed26280faa25871a0e544; real hook commit 2f266c9ee441d0514cf839f0565df6b0cc972c51. The final report commit/tag hash cannot be printed inside the PDF that is itself committed; the submission handoff gives that hash."),
        paragraph("I kept the prior HW6 report and unrelated working-tree changes out of the HW7 commits. Raw evidence and source snapshots are in reports/hw07/raw/."),
        paragraph("Part 1 — JWT, roles, and Ruff", PART),
        paragraph("The existing rental routes now require one JWT bearer scheme. MySQL users have unique username, password_hash, and reader/writer/moderator role; old session routing is not active on these routes. The pre-migration MySQL backup was kept privately outside Git."),
    ]
    evidence(story, "JWT HTTP cases", "Real requests show successful login and role actions plus 401/403 failures. The JWT is masked.",
             "POST /auth/login; GET /auth/me\nGET /api/listings; POST /api/listings; DELETE /api/listings/{id}", "07_auth_statuses.png")
    evidence(story, "Ruff failure", "Ruff caught two unused imports before the fix.",
             "ruff check hw7_bike_agent.py", "01_ruff_failure.png")
    evidence(story, "Ruff fixed", "After removing those unused imports, the same check passed.",
             "ruff check hw7_bike_agent.py", "02_ruff_success.png")
    evidence(story, "Commit hook", "The configured Ruff hook passed during a real VS Code terminal commit.",
             "git commit -m 'Record HW7 missing-ID run log'", "13_commit_hook.png")

    story.append(paragraph("Part 2 — Hand-written tool agent", PART))
    story.append(paragraph("The agent uses the existing local-model adapter and rental tools, appends tool observations, and bounds steps, tools, and tokens. The three fixed cases all make multiple real calls. One limited-search count claim was rejected by the verifier rather than reported as a success."))
    evidence(story, "A, B, C and missing ID", "A searches then inspects, B aggregates then inspects, C compares two details; an unknown ID returns not found.",
             "run_agent(TASKS[task], task=task)\nrun_agent('Inspect listing ID 9999999')", "08_agent_tasks.png")
    evidence(story, "Twenty attempts", "Under the same model settings, 13/20 were verified; the five required tool-call failure categories were all zero.",
             "python3 show_hw7_evidence.py reliability", "08b_reliability.png")

    story.append(paragraph("Part 3 — Reflexion", PART))
    story.append(paragraph("The deterministic verifier checks the exact observed listing facts. Reflexion permits at most two retries with cumulative 12-tool and 12,000-token budgets. It finished 3/3 tasks versus the baseline's 13/20 trials; one task used two retries. The controlled tight-step probe shows a failed then successful retry. No final verifier false rejection was observed."))
    evidence(story, "Failed then retried", "The trace shows the rejected unsupported count, scoped reflection, retries, and the probe's budget-exhausted first attempt.",
             "run_reflexion(task)  # at most two retries\npython3 show_hw7_evidence.py reflexion", "09_reflexion.png")

    story.append(paragraph("Part 4 — Divvy ReAct agent", PART))
    story.append(paragraph("This is a separate LangGraph StateGraph ReAct loop with csv_sql, policy_retriever, and calculator. Both CSVs contain 500 genuine anonymized January 2026 Divvy trip rows; scenario_selected marks a modeled rider subset. Tool JSON schemas and the common envelope are in hw7_bike_tools.py. Pricing snapshot URL, UTC access time, and SHA-256 are saved in raw/divvy_sources.json."))
    evidence(story, "Official prices", "The real Divvy page provides the classic-bike single-ride and annual membership terms used below.",
             "PRICE_URL = 'https://divvybikes.com/pricing'\n# $1 + $0.20/min; $143.90/year billed upfront", "06_official_pricing.jpg", 380)
    evidence(story, "Frequent rider", "The browser's 48 selected rides favor membership: $1,571.88 projected pay/use year versus $143.90 annual upfront. Monthly $11.99 is a comparison equivalent, not a bill.",
             "analyze_bike(divvy_member_csv, PRICE_URL)", "03_bike_member_ui.jpg", 385)
    evidence(story, "Tool timeline", "The live UI shows two read-only CSV queries, sourced pricing retrieval, calculator, and observations.",
             "csv_sql -> csv_sql -> policy_retriever -> calculator", "04_bike_member_timeline.jpg", 385)
    evidence(story, "Sparse rider", "The distinct 500-row sample selects three rides; $78.12 projected annual pay/use beats $143.90 upfront.",
             "analyze_bike(divvy_sparse_csv, PRICE_URL)", "05_bike_sparse_ui.jpg", 385)

    story.append(KeepTogether([
        paragraph("Part 5 — Prompt injection", PART),
        paragraph("I wrote three goals and preconditions in THREAT_MODEL.md before testing. A hostile local pricing fixture was tested in a 3-by-3 matrix. Recommendation override caused one wrong answer before defenses and one with prompt defense alone; prompt plus deterministic cost/tool checks corrected it. The model did not attempt non-SELECT SQL or repeat the contaminating phrase in these trials. The independent read-only SQL gate rejected the hostile DELETE probe."),
    ]))
    evidence(story, "Nine isolated tests", "The terminal shows actual outcomes for override, SQL and contamination across all three defense conditions.",
             "python3 show_hw7_evidence.py injection", "10_injection_matrix.png")

    story.append(KeepTogether([
        paragraph("Part 6 — Sandbox tools", PART),
        paragraph("Six file tools use sandbox-relative paths. confirm_bash reports a reason, SAFE_PREFIXES limits commands, and pure-Python is_destructive blocks risky operations even with auto_approve=True. The temporary sandbox found two DEBUG matches in three Python files; five safe cases ran and five risky cases were refused."),
    ]))
    evidence(story, "File search and gate", "This is the real combined sandbox run, not reconstructed output.",
             "python3 run_hw7_sandbox.py", "11_sandbox.png")

    story.append(paragraph("Final checks", PART))
    evidence(story, "Live smoke test", f"The final live test passed {sum(check['passed'] for check in verification['checks'])}/{len(verification['checks'])} objective checks, including HTTP roles and the bike endpoint.",
             "python3 verify_hw07.py --stdout-only --brief", "12_verification.png")
    story.append(PageBreak())
    story.append(paragraph("AI use", PART))
    story.append(paragraph("1. I used AI to draft and revise Python, React, tests, and this report, then checked the real local outputs."))
    story.append(paragraph("2. An unsuitable output chose pay/use despite $2,160/year versus $143.90 membership. Another called a limited three-row listing search a total."))
    story.append(paragraph("3. I found these by checking the costs and tool observations, then ran the live smoke, lint, UI, and gate tests."))
    story.append(paragraph("4. I added a deterministic cost boundary and a verifier rule for unsupported count claims. The read-only SQL gate is independent of the prompt. Full answers are in AI_USE.md."))
    story.append(paragraph("Repository and access", PART))
    story.append(paragraph("Repository URL: https://github.com/farzaandalwai/data260-0686. I did not add collaborator permissions. The installed GitHub CLI credentials were invalid, so existing access for Sbnikitha and supriyaselvanganesan could not be independently verified here; the owner should check the exact accounts in repository settings before submission."))
    document = SimpleDocTemplate(str(OUTPUT), pagesize=PAGE, leftMargin=35, rightMargin=35, topMargin=30, bottomMargin=30, title="Dalwai DATA 260 HW7", author="Farzaan Dalwai")
    document.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    from hw7_build_report_v2 import main as revised_main

    revised_main()
