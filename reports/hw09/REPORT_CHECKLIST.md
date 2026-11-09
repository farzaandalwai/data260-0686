# HW9 requirement cross-check

Assignment reviewed: all seven pages of the supplied Data260_HW9.pdf, including the inherited HW8 repository/configuration instructions. The PDF controls over demo.py and caching_agents.py.

## Implemented and measured

- Part 1: RentalCache.increment_listing_views uses Redis INCR, returns the count, and syncs MySQL every ten. raw/views.json records all 25 accesses and the two syncs. Original counter and all original rental fields were restored.
- Part 2: authenticated ingress in the existing FastAPI app; optional existing send_question.py --cache. Real Redis FLOAT32/COSINE vector index, local embedding model, final-answer/version storage, actual HW8 Kafka/local-model miss and hit bypass. raw/cache_requests.json has 12 requests, flags, scores and measured latency. raw/kafka contains the actual stage events. METRICS.md reports the measured hit/miss means and incorrect answers.
- Part 3.1: cache_cases.yaml has exactly 40 fixed labels (10 each), committed as 0cdc5328e78881f95f5756247ba0ee95c55162a6 before measurements; unchanged SHA checked.
- Parts 3.2/3.4: all five thresholds, all 200 case results in raw/threshold_cases.json and .csv; completed table in METRICS.md. Miss=1 and false hit=20 were fixed in EXPERIMENT_PLAN.md before measurements. Shipped threshold 0.95 minimizes that stated cost.
- Part 3.3: raw/false_hit.json contains both queries, 0.90014946 score, returned listing 8 code and correct listing 18 code. The report explains numeric-ID confusion.
- Part 3.5: raw/staleness.json records actual units 1 -> 8, stale answer 1 at version 2, invalidation to version 3 and fresh answer 8. The row/timestamp was restored; current version is 4. Ordinary API writes bump the SQL version transactionally. Global invalidation and explicit handling of out-of-band SQL are documented.
- Part 4 datasets: hw9_reference.json contains 70 actual rental records. training_data.json / validation_data.json / test_data.json contain only inputs (4/6/8), with disjoint questions. Frozen test SHA is identical across the four final runs.
- Part 4.1: hw9_agents.py contains the Answering Agent, deterministic Evaluator Agent and maximum-two-attempt feedback loop. raw/repair_with_memory.json records the complete deliberately incomplete first answer and successful second answer. Earlier two-attempt REVISE controls remain in raw/repair_demo.json.
- Part 4.2: lessons.json has all five fields. The training-derived lesson is saved/reloaded and raw/lesson_reuse.json records the later related question loading it.
- Part 4.3: raw/lesson_validation.json shows validation before/after (6/6 -> 5/6), the regression, rejection and omission of candidate lesson_002 from shipped memory. No held-out result was used to create lessons or tune the system.
- Part 4.4: raw/agent_variants.json records four independent memory copies and unchanged held-out inputs. METRICS.md and the report source contain the complete required table. Communication, reuse, two-attempt stopping, validation and limitations are explained.
- Repository evidence: real timestamped RUN_LOG.txt, machine-readable raw records, METRICS.md, truthful four-answer AI_USE.md and verification.json. 52/52 objective checks pass, including existing HW8, authentication, MySQL, MongoDB and MCP behavior. React build/lint pass.

## Report review and publication

- Native Mac capture initially returned stale VS Code images and noWindowsAvailable. Incorrect-stage captures were moved to ignored .hw9_runtime/capture_debug/ and are not report proof. After the user unlocked the Mac, all 15 report captures were taken through computer control from the updating VS Code terminal; each visibly includes Farzaan Dalwai, command and UTC time. The helper explicitly labels saved actual runs; the index inspection is live.
- The 16-page plain report source is build_hw9_report.py (14/12/11 pt main headings/subheadings/body; no decorative boxes or footers). Crop rectangles are in screenshots/crop_boxes.json. SCREENSHOT_MANIFEST.md maps all 15 captures to the exact PDF requirement, report section and page. provenance.json records unchanged originals, crop rectangles and both SHA256 values.
- Every page was rendered with Poppler and inspected visually for legibility, spacing, complete screenshots, correct excerpts and tables. Part 1 is page 2; Part 2 is pages 3-5; Part 3.1 is page 6; Parts 3.2/3.4 are page 7; Part 3.3 is page 8; Part 3.5 is page 9; Part 4 datasets are page 10; Parts 4.1-4.4 are pages 11-14; verification is page 15; truthful AI use is page 16. Setup/configuration is page 1.
- The tracked PDF uses symbolic hw9. The post-tag submission PDF resolves the actual final hash, avoiding a self-referential commit claim. See README.md for exact post-tag verification/export commands and the hw9 GitHub release for publication artifacts; verify remote hashes and downloaded PDF bytes before submitting.
- Exact required collaborator membership remains unconfirmed: the API reported public read permission but listed_collaborator=false for Sbnikitha and supriyaselvanganesan. No access changes were made.
