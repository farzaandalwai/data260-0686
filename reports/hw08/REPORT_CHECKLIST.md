# HW8 report cross-check

The controlling Data260_HW8.pdf was read on all eight pages. The two-page JMeter reference was also read; its unrelated direct-user demo was not substituted for the rental-domain requirements.

- Section 0: report page 1 has repository, all six configuration values, hardware/model, verified collaborator names/access, and the tag reference. The post-tag release PDF resolves the exact numeric tagged commit without a self-referential Git hash.
- Repository files: RUN_LOG.txt, raw CSV/JSON/events, METRICS.md, four AI_USE.md answers, report.pdf alias, named submission PDF, and verify_hw08.py/verification.json are included. Final tagged smoke output and resolved PDF are release assets.
- Part 1 operations/general requirements: pages 3-6 show rental validation, generated UUID, dictionary state, GET, unknown/missing/invalid inputs, clean errors, and preserved correlation IDs.
- Part 1 screenshots V.1: page 1 shows actual Docker containers, worker-ready output, and published FastAPI port 8686.
- Part 1 screenshots V.2-4: page 5 shows both successful responses and the complete CREATE -> GET send/receive/process/reply/client sequence; page 4 shows the real API wrapper response.
- Part 1 source screenshots: pages 2-3 show the Kafka client, demo, worker, and wrapper. Page 5 identifies the exact two topics and request/response fields; source and raw JSON provide their actual schemas.
- Part 2 topics: page 7 shows the real Kafka CLI create/describe output with two task partitions.
- Part 2 agents/code: pages 8-9 show separate processes, wrappers, plan/write/review excerpts, actual complete topic journey, and final status/answer/correlation JSON.
- Part 2 coordination explanation: page 9 explains buffered Kafka hand-offs without direct agent calls.
- Part 3 duplicate: page 10 shows actual unsafe baseline effects, fixed replay skip, and unchanged entity UUID.
- Part 3 death: page 11 shows SIGKILL/restart, redelivery of offset 62, and commit 63 after completion; the early-commit baseline is identified separately.
- Part 3 poison: page 12 shows three attempts, the dead-letter record/topic, and later task progress.
- Part 3 ordering: pages 13-14 show all 20 actual completions for each run, seed 260686, two Writers in one group, partitions, offsets, timestamps, and entity-key code.
- Part 3 table/comparison: page 15 has all four before/after rows and exactly two benefits and two responsibilities compared with HW2.
- Verification: page 16 shows 39/39 objective checks, including preservation of 5,000 MySQL listings, existing MongoDB/authentication/MCP checks; React build/lint logs are in raw/.
- AI use: page 17 repeats all four truthful answers from AI_USE.md.
- Formatting: main headings are bold 14 pt, subheadings bold 12 pt, body 11 pt; code is separate compact monospace. No decorative boxes or bottom footers. All terminal screenshots include the name, actual command, real output, and UTC capture timestamp.
- Screenshot provenance: screenshots/SCREENSHOT_MANIFEST.md maps captures to exact requirements and sections; provenance.json records crop rectangles and original/crop SHA-256 hashes. Original native screenshots remain unchanged.

Every rendered page was visually inspected; spacing was corrected after the first render. The final resolved release PDF is re-rendered and checked after the actual tag exists. Earlier failed experiment attempts remain available and are not presented as the final measurements.
