"""Build the plain HW8 report from source excerpts and native screenshots."""

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports/hw08"
SHOTS = REPORT / "screenshots"
WIDTH, HEIGHT = landscape(A4)
FONT, BOLD = "Helvetica", "Helvetica-Bold"
FONT_ROOT = Path("/System/Library/Fonts/Supplemental")
if (FONT_ROOT / "Arial.ttf").exists():
    pdfmetrics.registerFont(TTFont("HW8Arial", str(FONT_ROOT / "Arial.ttf")))
    pdfmetrics.registerFont(TTFont("HW8ArialBold", str(FONT_ROOT / "Arial Bold.ttf")))
    FONT, BOLD = "HW8Arial", "HW8ArialBold"
BODY = ParagraphStyle("body", fontName=FONT, fontSize=11, leading=14)

EVIDENCE = [
    ("01_services", "Part 1 V.1", "Setup", "docker ps; worker ready and FastAPI startup logs"),
    ("04_client_demo_code", "Part 1 source screenshots", "Client and demo", "nl -ba hw8_kafka.py (85-96); homework_demo.py (7-24)"),
    ("05_worker_api_code", "Part 1 source screenshots", "Worker and API", "nl -ba hw8_worker.py (27-51); routers/hw8_listings.py (16-23)"),
    ("16_api", "Part 1 II and V.2-3", "API response", "curl POST /api/hw8/listings with saved listing UUID and caller correlation ID"),
    ("02_roundtrip", "Part 1 IV and V.2-4", "CREATE then GET", "python show_hw8_evidence.py roundtrip; reads raw/round_trip.json"),
    ("15_validation", "Part 1 III", "Validation", "python show_hw8_evidence.py checks | head -n 23"),
    ("03_topics", "Part 2 II", "Topics", "bash scripts/hw8_topics.sh; Kafka CLI create and describe"),
    ("06_agents", "Part 2 III and Submit code", "Separate agents", "cat planner.py writer.py reviewer.py; docker top each agent"),
    ("07_journey", "Part 2 IV and Submit journey/final JSON", "Message journey", "python show_hw8_evidence.py journey; reads raw events and agent_journey.json"),
    ("08_duplicate", "Part 3 I and Submit logs", "Duplicate delivery", "python show_hw8_evidence.py duplicate"),
    ("09_death", "Part 3 II and Submit logs", "Consumer death", "python show_hw8_evidence.py death"),
    ("10_poison", "Part 3 III and Submit logs", "Poison message", "python show_hw8_evidence.py poison"),
    ("11_unkeyed", "Part 3 IV and Submit logs", "Unkeyed ordering", "python show_hw8_evidence.py unkeyed; all 20 raw CSV rows"),
    ("12_keyed", "Part 3 IV and Submit logs", "Keyed ordering", "python show_hw8_evidence.py keyed; all 20 raw CSV rows"),
    ("13_verification", "Repository verification.json", "Verification", "python show_hw8_evidence.py checks | tail -n 19"),
]


def read_json(name):
    return json.loads((REPORT / name).read_text())


def crop_screenshots():
    provenance = []
    for stem, requirement, section, command in EVIDENCE:
        original = SHOTS / "originals" / (stem + ".png")
        with Image.open(original) as image:
            # Only remove unused window chrome/blank terminal space. Never redraw evidence.
            pixels = image.convert("RGB")
            last = 260
            for row in range(205, min(image.height - 100, 1620)):
                if any(max(pixels.getpixel((col, row))) > 145 for col in range(200, 2655, 3)):
                    last = row
            box = (185, 200, min(2670, image.width), min(last + 18, image.height))
            target = SHOTS / (stem + ".png")
            image.crop(box).save(target)
        provenance.append({"file": target.name, "original": "originals/" + original.name,
                           "crop_box": box, "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                           "cropped_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                           "requirement": requirement, "section": section, "command": command})
    (SHOTS / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    lines = ["# HW8 screenshot manifest", "", "All terminal captures were taken with computer control from the real VS Code terminal on this Mac. Originals are retained unchanged; report images are crops only. Display helpers format saved actual runs, not fabricated output. Every terminal capture includes Farzaan Dalwai, the command, and UTC capture time.", ""]
    for row in provenance:
        lines += [f"## {row['file']}", f"- PDF requirement: {row['requirement']}",
                  f"- Report section: {row['section']}", f"- Command/evidence: `{row['command']}`", ""]
    lines += ["## Supplemental capture", "`originals/14_react.png` is the existing React login-required page inspected in the browser; it is not used as proof of authenticated functionality and is not duplicated in the report.", ""]
    (SHOTS / "SCREENSHOT_MANIFEST.md").write_text("\n".join(lines))


def failure_rows(result):
    return [
        ["Duplicate delivery", f"{result['before']['duplicate']['side_effects']} effects for one correlation ID.",
         f"{result['duplicate']['new_drafts']} draft; replay skipped. CREATE replay returned the same UUID."],
        ["Consumer killed mid-work", f"Early commit {result['before']['early']['committed_after_kill']}; source offset {result['before']['early']['source_offset']}; 0 original effects.",
         f"Offset {result['death']['source']['offset']} received twice; committed stayed {result['death']['committed_after_kill']} at kill and became {result['death']['committed_after_success']} after completion."],
        ["Poison message", f"{result['before']['poison']['observed_retries_before_kill']} observed retries before stopping; later message blocked.",
         f"{result['poison']['retry_count']} attempts, s0686_dead_letter, later message completed."],
        ["Two partitions/two consumers", "Unkeyed: 20 completions across partitions 0 and 1; completion order differed from send order.",
         "Entity key rental-0686: all 20 in partition 0, completed 1 through 20."],
    ]


def write_metrics(result):
    lines = ["# HW8 measured results", "", f"Final experiment run: `{result['run_id']}`. VERIFY_SEED: 260686. Sources: `raw/failure_results.json`, `raw/ordering_input.json`, and both ordering CSV files. Before-fix consumers are deliberately unsafe experimental baselines, not application services.", "", "| Failure scenario | Before fix | After fix |", "|---|---|---|"]
    lines += ["| " + " | ".join(row) + " |" for row in failure_rows(result)]
    for mode in ("unkeyed", "keyed"):
        data = result[mode]
        lines += ["", f"## {mode.title()}", f"- Count: {len(data['processed'])}", f"- Partitions: {data['partitions']}",
                  f"- Active processing instances: {data['instances']}", f"- Completion order: {data['observed_order']}",
                  f"- Matches send order: {data['in_order']}"]
    lines += ["", "Two group members held one task partition each. Unkeyed messages were deliberately distributed round-robin without a key, with seeded payloads/delays. In the keyed run, one Writer owned the entity's single partition while the other remained in the group. This measures completion order and does not imply Kafka reorders records within a partition.", "", "The entity dictionary/cache is process-local. The pipeline's SQLite cache survives Writer restart, but an output publish/mark-sent crash window can still cause downstream duplicate delivery; downstream stages also deduplicate. No end-to-end exactly-once claim is made.", ""]
    (REPORT / "METRICS.md").write_text("\n".join(lines))


class Report:
    def __init__(self, destination):
        self.canvas = Canvas(str(destination), pagesize=(WIDTH, HEIGHT), pageCompression=1)
        self.canvas.setTitle("DATA 260 HW8 - Farzaan Dalwai")
        self.canvas.setAuthor("Farzaan Dalwai")
        self.page = 0
        self.y = HEIGHT - 30

    def start(self, title, subtitle=None):
        if self.page:
            self.canvas.showPage()
        self.page += 1
        self.y = HEIGHT - 30
        self.canvas.setFont(BOLD, 14)
        self.canvas.drawString(30, self.y, title)
        self.y -= 23
        if subtitle:
            self.sub(subtitle)

    def sub(self, text):
        self.y -= 12
        self.canvas.setFont(BOLD, 12)
        self.canvas.drawString(30, self.y, text)
        self.y -= 20

    def body(self, text):
        paragraph = Paragraph(escape(text), BODY)
        _, height = paragraph.wrap(WIDTH - 60, HEIGHT)
        if self.y - height < 25:
            raise ValueError(f"Text overflows page {self.page}")
        paragraph.drawOn(self.canvas, 30, self.y - height)
        self.y -= height + 7

    def excerpt(self, name, start, end):
        self.body(f"{name}, lines {start}-{end} (excerpt; surrounding lines omitted)")
        lines = (ROOT / name).read_text().splitlines()[start - 1:end]
        self.canvas.setFont("Courier", 8.5)
        for line in lines:
            for wrapped in textwrap.wrap(line.expandtabs(4), width=149, replace_whitespace=False, drop_whitespace=False) or [""]:
                self.canvas.drawString(30, self.y, wrapped)
                self.y -= 10
        self.y -= 3

    def shot(self, stem):
        path = SHOTS / (stem + ".png")
        with Image.open(path) as image:
            width, height = image.size
        scale = min((WIDTH - 60) / width, (self.y - 28) / height)
        if scale < 0.22:
            raise ValueError(f"Screenshot too small on page {self.page}: {stem}")
        self.canvas.drawImage(str(path), 30, self.y - height * scale, width * scale, height * scale)
        self.y -= height * scale + 8

    def table(self, rows):
        wrapped = [[Paragraph(escape(cell), BODY) for cell in row] for row in rows]
        table = Table(wrapped, colWidths=[155, 235, WIDTH - 450])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("GRID", (0, 0), (-1, -1), 0.4, "black"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                   ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                   ("TOPPADDING", (0, 0), (-1, -1), 6),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        _, height = table.wrap(WIDTH - 60, HEIGHT)
        table.drawOn(self.canvas, 30, self.y - height)
        self.y -= height + 12


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tagged-commit", help="Resolved only after the actual hw8 tag exists")
    parser.add_argument("--output", default=str(REPORT / "Dalwai_HW8.pdf"))
    args = parser.parse_args()
    crop_screenshots()
    result = read_json("raw/failure_results.json")
    verification = read_json("verification.json")
    write_metrics(result)
    report = Report(Path(args.output))
    report.start("DATA 260 HW8 - Farzaan Dalwai", "Setup")
    report.body("Repository: https://github.com/farzaandalwai/data260-0686")
    report.body("SID4 0686 | PORT_BASE 8686 | PREFIX s0686 | SEED 686 | VERIFY_SEED 260686 | DOMAIN_ID 6 - Rental Housing Listings")
    report.body("Hardware: Apple M4, 24 GiB RAM, macOS 26.6.2 arm64. Python 3.11.14; Kafka 4.1.2; Docker 29.7.2. Local model: llama3.2:latest via the existing Ollama adapter; failure/order tests use facts-only output.")
    report.body("Tagged commit: " + (args.tagged_commit or "hw8 (numeric hash is resolved in the post-tag submission artifact; git rev-parse hw8^{commit})."))
    report.body("GitHub API checked the working public repository and read access for Sbnikitha and supriyaselvanganesan at 2026-11-02 04:42 UTC; no permissions were changed.")
    report.excerpt("hw8_start_api.py", 10, 11)
    report.shot("01_services")

    report.start("Part 1 - Client and demo")
    report.body("One correlation ID is created for each request, and CREATE's returned UUID is passed to GET.")
    report.excerpt("homework_demo.py", 13, 16)
    report.shot("04_client_demo_code")

    report.start("Part 1 - Worker and API")
    report.body("The worker validates rental fields and stores UUID-keyed listings in a plain dictionary; the existing FastAPI app forwards requests through Kafka.")
    report.excerpt("hw8_worker.py", 54, 57)
    report.shot("05_worker_api_code")

    report.start("Part 1 - API response")
    report.body("The real API GET preserved the caller's correlation ID and returned the listing created by the demo.")
    report.excerpt("routers/hw8_listings.py", 16, 23)
    report.shot("16_api")

    report.start("Part 1 - CREATE then GET")
    report.body("Topics: s0686_entity_requests -> s0686_entity_responses; each request has correlation_id, reply_to, operation, data, and each reply echoes correlation_id with success plus listing_id/listing or error.")
    report.excerpt("hw8_kafka.py", 85, 94)
    report.shot("02_roundtrip")

    report.start("Part 1 - Validation")
    report.body("Actual checks reject missing or invalid fields, unknown operations, and missing/unknown IDs while preserving the request correlation ID on errors.")
    report.excerpt("hw8_worker.py", 10, 17)
    report.shot("15_validation")

    report.start("Part 2 - Topics")
    report.body("Kafka CLI created/described all required topics; s0686_tasks has two partitions, and the other six have one each.")
    report.excerpt("scripts/hw8_topics.sh", 3, 12)
    report.shot("03_topics")

    report.start("Part 2 - Separate agents")
    report.body("Planner, Writer, and Reviewer run in distinct container processes; each wrapper consumes its source topic and publishes to the next topic.")
    report.excerpt("hw8_pipeline.py", 13, 17)
    report.excerpt("hw8_pipeline.py", 34, 41)
    report.shot("06_agents")

    report.start("Part 2 - Message journey")
    report.body("Kafka buffers the hand-offs without direct agent calls: inbox -> Planner -> tasks -> Writer -> drafts -> Reviewer -> final; the final JSON preserves correlation_id, status, and answer.")
    report.excerpt("hw8_pipeline.py", 26, 31)
    report.shot("07_journey")

    report.start("Part 3 - Duplicate delivery")
    report.body("The unsafe baseline made two effects; replaying the fixed pipeline correlation ID made one draft, and replaying CREATE returned the same UUID.")
    report.excerpt("hw8_pipeline.py", 59, 63)
    report.shot("08_duplicate")

    report.start("Part 3 - Consumer death")
    report.body("The early-commit baseline lost unfinished work; the fixed Writer received task offset 62 again after SIGKILL and committed 63 only after successful completion.")
    report.excerpt("hw8_pipeline.py", 109, 115)
    report.excerpt("hw8_pipeline.py", 127, 129)
    report.shot("09_death")

    report.start("Part 3 - Poison message")
    report.body("The unsafe consumer kept retrying and blocked the next task; the fixed Writer tried three times, published to s0686_dead_letter, and completed the later task.")
    report.excerpt("hw8_pipeline.py", 119, 126)
    report.shot("10_poison")

    report.start("Part 3 - Unkeyed ordering")
    report.body("The 20 seeded related messages were round-robin distributed without a key; two Writers completed them out of global send order, while each partition retained its own order.")
    report.excerpt("run_hw8_experiments.py", 189, 192)
    report.shot("11_unkeyed")

    report.start("Part 3 - Keyed ordering")
    report.body("The same seeded messages used key rental-0686, all reached partition 0, and completed 1-20; the second Writer stayed in the same group but did not own that entity's partition.")
    report.excerpt("run_hw8_experiments.py", 112, 117)
    report.shot("12_keyed")

    report.start("Part 3 - Failure table and HW2 comparison")
    report.table([["Failure scenario", "Before fix", "After fix"], *failure_rows(result)])
    report.sub("Two benefits")
    report.body("1. Independent scaling: a second Writer shares the two task partitions without changing Planner or Reviewer. 2. Decoupled failure: a Writer can restart and resume its Kafka input while the other processes remain separate, unlike HW2's waiting function calls in one LangGraph process.")
    report.sub("Two responsibilities")
    report.body("1. Handle duplicate delivery and recovery: keep idempotency state, commit only after success, and bound poison retries. 2. Choose partition keys for entity order: Kafka does not provide one global processing order across partitions, so related messages need a shared key.")
    report.body("Limits: the exercise entity dictionary is process-local; the pipeline uses persistent SQLite deduplication, but a publish/mark-sent crash window can still cause downstream duplicates. This is not an end-to-end exactly-once system. Single-broker recreation also loses this local exercise's Kafka data.")

    report.start("Verification")
    report.body(f"The objective smoke test passed {sum(row['passed'] for row in verification['checks'])}/{len(verification['checks'])} checks; React build/lint also passed and all 5,000 existing rental rows remained unchanged.")
    report.excerpt("verify_hw08.py", 35, 38)
    report.shot("13_verification")

    report.start("AI use")
    answers = (REPORT / "AI_USE.md").read_text().split("\n\n")[1:]
    headings = ["1. AI help and my contribution", "2. Wrong or unsuitable output", "3. How it was checked", "4. Changes and why they work"]
    for heading, answer in zip(headings, answers):
        report.sub(heading)
        report.body(answer[3:])
    report.canvas.save()
    print(f"Created {args.output}: {report.page} pages")


if __name__ == "__main__":
    main()
