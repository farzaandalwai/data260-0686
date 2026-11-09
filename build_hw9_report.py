"""Build the plain HW9 report from real source excerpts and native captures."""

import argparse
import hashlib
import json
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports/hw09"
SHOTS = REPORT / "screenshots"
WIDTH, HEIGHT = landscape(A4)
FONT, BOLD = "Helvetica", "Helvetica-Bold"
FONTS = Path("/System/Library/Fonts/Supplemental")
if (FONTS / "Arial.ttf").exists():
    pdfmetrics.registerFont(TTFont("HW9Arial", str(FONTS / "Arial.ttf")))
    pdfmetrics.registerFont(TTFont("HW9ArialBold", str(FONTS / "Arial Bold.ttf")))
    FONT, BOLD = "HW9Arial", "HW9ArialBold"
BODY = ParagraphStyle("body", fontName=FONT, fontSize=11, leading=14)

EVIDENCE = [
    ("01_services", "Inherited repository instructions: working system/configuration", "Setup", 1, "docker ps --filter name=s0686-hw8 --format 'table {{.Names}}  {{.Status}}'"),
    ("02_views", "Part 1: INCR on accesses 1-25; MySQL syncs at 10 and 20", "Part 1 - Views", 2, "python show_hw9_evidence.py views"),
    ("03_index", "Part 2: real Redis vector index and cosine embeddings", "Part 2 - Vector cache", 3, "python show_hw9_evidence.py index"),
    ("04_requests", "Part 2: at least ten requests; flags, scores, latency and measured hit/miss means", "Part 2 - Requests", 4, "python show_hw9_evidence.py requests"),
    ("05_journey", "Part 2: miss uses existing HW8 Kafka/local adapter; hit reuses final answer", "Part 2 - Pipeline", 5, "python show_hw9_evidence.py journey"),
    ("06_labels", "Part 3.1: exactly 40 labels committed before the sweep", "Part 3.1 - Frozen cases", 6, "python show_hw9_evidence.py labels"),
    ("07_thresholds", "Parts 3.2 and 3.4: five thresholds, filled metrics, cost choice", "Parts 3.2/3.4 - Thresholds", 7, "python show_hw9_evidence.py thresholds"),
    ("08_false_hit", "Part 3.3: complete observed false hit", "Part 3.3 - False hit", 8, "python show_hw9_evidence.py falsehit"),
    ("09_stale", "Part 3.5: actual SQL change, stale answer, invalidation and restoration", "Part 3.5 - Stale answer", 9, "python show_hw9_evidence.py stale"),
    ("10_datasets", "Part 4: separate reference facts and input-only train/validation/test datasets", "Part 4 - Datasets", 10, "python show_hw9_evidence.py datasets"),
    ("11_repair", "Part 4.1 / Required demonstration 1 and 3: Answering/Evaluator code, full revision and stop", "Part 4.1 - Repair", 11, "python show_hw9_evidence.py repair"),
    ("12_lessons", "Part 4.2 / Required demonstration 2: all five lesson fields and later reuse", "Part 4.2 - Lessons", 12, "python show_hw9_evidence.py lessons"),
    ("13_validation", "Part 4.3: before/after validation and rejection of regression", "Part 4.3 - Validation", 13, "python show_hw9_evidence.py validation"),
    ("14_variants", "Part 4.4 / Required demonstration 4: independent four-variant test table", "Part 4.4 - Held-out results", 14, "python show_hw9_evidence.py variants"),
    ("15_verification", "Inherited repository instructions: objective checks and earlier-homework regression", "Verification", 15, "python show_hw9_evidence.py checks | tail -n 18"),
]


def read(name):
    return json.loads((REPORT / name).read_text())


def prepare_crops():
    """Apply only explicitly reviewed crop rectangles to unmodified originals."""
    crops = read("screenshots/crop_boxes.json")
    provenance, manifest = [], ["# HW9 screenshot manifest", "", "Native Mac computer-control captures from the actual VS Code terminal. Each shows Farzaan Dalwai, the command and UTC capture time. Display helpers explicitly identify saved real runs; the index capture inspects live Redis. Report images are crops only. Originals remain unchanged.", ""]
    for stem, requirement, section, page, command in EVIDENCE:
        original, target = SHOTS / "originals" / (stem + ".png"), SHOTS / (stem + ".png")
        box = crops[stem]
        with Image.open(original) as image:
            assert 0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height
            image.crop(box).save(target)
        provenance.append({"file": target.name, "original": "originals/" + original.name,
                           "crop_box": box, "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                           "cropped_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                           "requirement": requirement, "report_section": section, "report_page": page, "command": command})
        manifest += [f"## {target.name}", f"- Exact requirement: {requirement}", f"- Report: page {page}, {section}", f"- Command: `{command}`", ""]
    (SHOTS / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (SHOTS / "SCREENSHOT_MANIFEST.md").write_text("\n".join(manifest))


class Report:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.canvas = Canvas(str(path), pagesize=(WIDTH, HEIGHT), pageCompression=1)
        self.canvas.setTitle("DATA 260 HW9 - Farzaan Dalwai")
        self.canvas.setAuthor("Farzaan Dalwai")
        self.page, self.y = 0, HEIGHT - 30

    def start(self, title, subheading):
        if self.page:
            self.canvas.showPage()
        self.page += 1
        self.y = HEIGHT - 30
        self.canvas.setFont(BOLD, 14)
        self.canvas.drawString(30, self.y, title)
        self.y -= 23
        self.canvas.setFont(BOLD, 12)
        self.canvas.drawString(30, self.y, subheading)
        self.y -= 21

    def body(self, text):
        paragraph = Paragraph(escape(text), BODY)
        _, height = paragraph.wrap(WIDTH - 60, HEIGHT)
        if self.y - height < 25:
            raise ValueError(f"Text overflow on page {self.page}")
        paragraph.drawOn(self.canvas, 30, self.y - height)
        self.y -= height + 7

    def excerpt(self, name, start, end):
        self.body(f"{name}, lines {start}-{end} (excerpt; surrounding lines omitted)")
        lines = (ROOT / name).read_text().splitlines()[start - 1:end]
        self.canvas.setFont("Courier", 8.5)
        for line in lines:
            for wrapped in textwrap.wrap(line.expandtabs(4), width=149, subsequent_indent="    ", replace_whitespace=False, drop_whitespace=False) or [""]:
                self.canvas.drawString(30, self.y, wrapped)
                self.y -= 10
        self.y -= 4

    def shot(self, stem):
        path = SHOTS / (stem + ".png")
        with Image.open(path) as image:
            width, height = image.size
        scale = min((WIDTH - 60) / width, (self.y - 25) / height)
        if scale < 0.22:
            raise ValueError(f"Screenshot too small on page {self.page}: {stem}, scale {scale}")
        self.canvas.drawImage(str(path), 30, self.y - height * scale, width * scale, height * scale)
        self.y -= height * scale + 7

    def table(self, rows, widths):
        wrapped = [[Paragraph(escape(str(cell)), BODY) for cell in row] for row in rows]
        table = Table(wrapped, colWidths=widths)
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("GRID", (0, 0), (-1, -1), 0.4, "black"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        _, height = table.wrap(WIDTH - 60, HEIGHT)
        table.drawOn(self.canvas, 30, self.y - height)
        self.y -= height + 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tagged-commit")
    parser.add_argument("--output", default=str(REPORT / "Dalwai_HW9.pdf"))
    args = parser.parse_args()
    prepare_crops()
    report = Report(Path(args.output))
    report.start("DATA 260 HW9 - Farzaan Dalwai", "Setup")
    report.body("Repository: https://github.com/farzaandalwai/data260-0686")
    report.body("SID4 0686 | PORT_BASE 8686 | PREFIX s0686 | SEED 686 | VERIFY_SEED 260686 | DOMAIN_ID 6 - Rental Housing Listings")
    report.body("Apple M4, 24 GiB RAM, macOS 26.6.2 arm64; Python 3.11.14; Kafka 4.1.2; Redis 8.2.2. Local Ollama: llama3.2:latest for answers, nomic-embed-text:latest for 768-dimensional embeddings.")
    report.body("Tagged commit: " + (args.tagged_commit or "hw9 (symbolic source reference; the post-tag release/submission PDF resolves the numeric hash)."))
    report.body("The existing app, local adapter and MySQL s0686_rel are extended. Original 5,000 records were preserved; private backups preceded the schema additions. GitHub read access was observed for Sbnikitha and supriyaselvanganesan, but exact collaborator membership was not confirmed and no access changes were made.")
    report.excerpt("compose.hw09.yml", 1, 9)
    report.shot("01_services")

    report.start("Part 1 - Views", "25 accesses")
    report.excerpt("hw9_cache.py", 81, 86)
    report.body("Redis INCR returns every new count; MySQL syncs at 10 and 20, and the demo restores its original counter afterward.")
    report.shot("02_views")

    report.start("Part 2 - Vector cache", "Redis cosine index")
    report.excerpt("hw9_cache.py", 89, 93)
    report.excerpt("hw9_cache.py", 120, 126)
    report.excerpt("hw9_cache.py", 128, 134)
    report.body("The Redis hash stores the query, FLOAT32 embedding, final answer and version; all keys/indexes begin with s0686 and entries expire after one hour.")
    report.shot("03_index")

    report.start("Part 2 - Requests", "Initial threshold 0.85")
    report.excerpt("hw9_cache.py", 144, 158)
    report.body("The 12 authenticated requests produced 8 hits (66.67%); mean hit/miss latency was 30.521/1665.960 ms, with four wrong returned answers. Handler timing includes embedding, version lookup, Redis and miss work; HTTP authentication is excluded.")
    report.shot("04_requests")

    report.start("Part 2 - Pipeline", "Real miss and repeated hit")
    report.excerpt("routers/hw9_cache.py", 21, 25)
    report.excerpt("hw9_cache.py", 99, 111)
    report.body("A miss traverses inbox -> Planner -> tasks -> Writer/local adapter -> drafts -> Reviewer -> final; the repeated hit returns the same final answer/correlation ID without publishing new Kafka work.")
    report.shot("05_journey")

    report.start("Part 3.1 - Frozen cases", "40 labels before the sweep")
    report.excerpt("scripts/hw9_freeze_cases.py", 22, 32)
    report.body("Commit 0cdc5328e78881f95f5756247ba0ee95c55162a6 fixed ten cases per category before measurements. Labels stayed unchanged; no labeling error was found. Each threshold starts from the same ten actual warm-up answers; benchmark misses do not add entries.")
    report.shot("06_labels")

    report.start("Parts 3.2 and 3.4 - Thresholds", "Measured trade-off")
    rows = [["Threshold", "Hit rate", "False-hit rate", "Mean latency (ms)", "Total cost"]]
    for row in read("raw/threshold_summary.json"):
        rows.append([f"{row['threshold']:.2f}", f"{row['hit_rate'] * 100:.1f}%", f"{row['false_hit_rate'] * 100:.1f}%", f"{row['mean_latency_ms']:.3f}", row["total_cost"]])
    report.table(rows, [120, 130, 140, 200, 190])
    report.body("Costs were fixed before the sweep: miss=1 for extra local inference work; false hit=20 for a wrong housing answer and support correction. These are normalized assumptions, not dollars. Total=misses+20*false_hits; false-hit rate=wrong cached answers/40. Ship 0.95: lowest cost (30), with zero false hits in this set; lower hit rate and higher mean latency are the trade-off.")
    report.excerpt("run_hw9_cache.py", 108, 114)
    report.shot("07_thresholds")

    report.start("Part 3.3 - False hit", "Observed confusion")
    report.excerpt("hw9_cache.py", 140, 147)
    report.body("Likely confusion: repeated listing-code wording outweighed the changed numeric record ID, returning another listing's answer; 0.95 is not a universal correctness guarantee.")
    report.shot("08_false_hit")

    report.start("Part 3.5 - Stale answer", "Version invalidation")
    report.excerpt("hw9_cache.py", 52, 61)
    report.excerpt("hw9_cache.py", 137, 142)
    report.body("Changing listing 2 from 1 to 8 units left the old cached answer at version 2; version 3 forced a fresh answer of 8. The original row/timestamp was restored and version advanced to 4. Normal API writes bump the version in the same SQL transaction; out-of-band SQL needs explicit invalidation. A global version invalidates unrelated answers and adds a SQL read on hits; Redis loss can lose up to nine unsynced views.")
    report.shot("09_stale")

    report.start("Part 4 - Datasets", "Facts separate from inputs")
    report.excerpt("scripts/hw9_freeze_cases.py", 37, 45)
    report.body("hw9_reference.json contains 70 real rental facts; the disjoint input-only files contain 4 training, 6 validation and 8 held-out questions. The same test bytes were first loaded after lesson selection and used unchanged across all four variants.")
    report.shot("10_datasets")

    report.start("Part 4.1 - Repair", "Answering Agent and Evaluator Agent")
    report.excerpt("hw9_agents.py", 23, 28)
    report.excerpt("hw9_agents.py", 46, 54)
    report.body("The local Answering Agent receives reference facts, lessons and feedback; the deterministic Evaluator checks values/types and unsupported fields. This training-only demo deliberately removes available_units on attempt 1, then uses evaluator feedback and the saved lesson to pass on attempt 2. Earlier no-memory controls remained REVISE at the same limit and are retained in raw/repair_demo.json.")
    report.shot("11_repair")

    report.start("Part 4.2 - Lessons", "Save, reload and reuse")
    report.excerpt("hw9_agents.py", 15, 22)
    report.excerpt("run_hw9_agents.py", 21, 26)
    report.body("Repeated training omissions created lesson_001 with lesson_id, failure_pattern, correction, created_at and use_count; the later related question reloads it from lessons.json before answering.")
    report.shot("12_lessons")

    report.start("Part 4.3 - Validation", "Reject the regression")
    report.excerpt("hw9_agents.py", 87, 95)
    report.body("The extra unknown-field lesson changed validation from 6/6 to 5/6: a previously correct answer regressed, so the candidate was rejected and removed. There were no failing baseline validation cases to worsen; unrelated questions stayed supported. The four held-out variants were then evaluated independently.")
    report.shot("13_validation")

    report.start("Part 4.4 - Held-out results", "Four independent variants")
    rows = [["Variant", "Correct", "Incorrect", "Average attempts", "Average latency (ms)"]]
    for name, row in read("raw/agent_variants.json").items():
        rows.append([name, row["correct"], row["incorrect"], f"{row['average_attempts']:.3f}", f"{row['average_latency_ms']:.3f}"])
    report.table(rows, [220, 95, 95, 175, 195])
    report.excerpt("hw9_agents.py", 61, 69)
    report.body("Agents exchange JSON answers and concise feedback; PASS stops immediately, otherwise repair stops after attempt 2. Each variant has its own lesson copy. Validated Improvement kept only the prior lesson because the candidate failed validation. Limitation: small test set and local model/runtime variation; memory did not outperform Evaluator Repair, and timings do not prove a general speedup.")
    report.shot("14_variants")

    report.start("Verification", "Objective checks")
    report.excerpt("verify_hw09.py", 36, 39)
    report.body("52/52 checks passed, covering counter sync/restoration, vector cache and Kafka bypass, all 200 sweep cases/costs, stale/fresh answers, datasets, lessons, validation and four held-out totals. Existing HW8 CREATE/GET and local-model path, JWT, MySQL, MongoDB/MCP checks passed; React build/lint also passed. All original fields of all 5,000 SQL rows retain SHA256 992fb523554a20337a31d94fbe7f7fdcbcbb809c7032c396f8e768563534cc0b.")
    report.shot("15_verification")

    report.start("AI use", "Four answers")
    for paragraph in (REPORT / "AI_USE.md").read_text().split("\n\n")[1:]:
        report.body(paragraph.strip())
    report.canvas.save()
    print(json.dumps({"output": args.output, "pages": report.page, "sha256": hashlib.sha256(Path(args.output).read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
