# HW6 requirement-to-evidence checklist

This checklist is derived from all eight pages of the controlling `DATA260_HW6.pdf`.

- [x] Configuration, hardware, model, implementation commit, proposed `hw6` tag, repository, and collaborator status appear at the report top.
- [x] `reports/hw06/` contains the required run log, raw data, metrics, AI use, verification JSON, screenshots, and report PDF; `Dalwai_HW6.pdf` is the named root submission copy.
- [x] MongoDB `s0686_doc.rental_documents` has Pydantic and `$jsonSchema` validation plus complete CRUD and required error paths.
- [x] Real CRUD, invalid-input, and MongoDB document screenshots are captured from the working system.
- [x] `messages`, `summaries`, and `episodes` have required fields and useful indexes in the same database.
- [x] `/api/chat`, `/api/memory/{user_id}`, and `/api/aggregate/{user_id}` work with short-, long-, and episodic memory.
- [x] A real 10-message session proves sliding window, both summary scopes, nonempty embeddings, cosine retrieval, and grounded replies.
- [x] Every normal chat request logs exact Ollama totals, estimated components, latency, identity, timestamp, condition, and configuration.
- [x] `memory_probes.yaml` has exactly five fixed probes, criteria, and a complete objective 1-5 rubric.
- [x] Four isolated 30-turn conditions use the same conversation and probes, with policy savings, quality/latency changes, and cost estimates.
- [x] Root `AGENT.md` has at least five instructions across the assignment categories and one function passes an objective compliance check.
- [x] Original `MEMORY.md` has exactly 55 qualifying lines, at least three duplicates, and at least three contradictions.
- [x] Original and consolidated root memory states are preserved in separate local commits and exact raw evidence copies.
- [x] Consolidation produces fewer than 40 lines, preserves conflict evidence, applies a transparent rule, and passes an independent outcome check.
- [x] `/memory`, `/compact`, `/dream`, and `/help` accept no paths and operate only on the known root memory files.
- [x] Report compares MongoDB and file memory on inspectability, restart persistence, scale, and must-not-forget facts.
- [x] Regression and security checks cover existing FastAPI/MySQL/auth, React build/lint, MCP imports, ignored `.env`, and secret exclusion.
- [x] Every terminal screenshot shows `Farzaan Dalwai — DATA 260 HW6`, the command, a timestamp, real output, and no private information.
- [x] `SCREENSHOT_MANIFEST.md` maps every live-system screenshot to the exact PDF requirement and report section.
- [x] Final PDF uses plain 14/12/11 pt styles, no decorative boxes or footers, places each short snippet immediately above its matching real screenshot, and passes page-by-page visual QA across all 11 pages.
- [x] No push, `hw6` tag creation, or collaborator access change occurred before user review.
