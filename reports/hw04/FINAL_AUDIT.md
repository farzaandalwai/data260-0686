# HW4 Final Audit

Verifier: `python3.11 verify_hw04.py`

`reports/hw04/verification.json` stores `tested_commit` and `overall_pass` for the commit under test. The script checks source text for the CRUD route guard. It does not open a browser.

## Part results

| Part | Result |
| --- | --- |
| Part 1 React login and MySQL CRUD | PASS |
| Part 2 Database, session cookie, and CRUD API | PASS |
| Part 3 N+1 benchmark, index, and EXPLAIN | PASS |
| Part 4 RAG retrieval, comparison, and evaluation | PASS |

## Screenshot coverage

44 screenshots are present under `reports/hw04/screenshots/`. Each file is a PNG larger than 20 KB. No required screenshot is missing.

Direct CRUD routes require a logged-in user in the React UI and on the API. `/create`, `/update`, `/update/:id`, `/delete`, and `/delete/:id` show “Login required” and a link to `/login` while logged out. The forms stay hidden during the initial `/api/auth/me` check. Logged-in CRUD behavior is unchanged. `HW4-REACT-ROUTE-GUARD.png` shows the logged-out `/create` page.

| Area | Files | Present | Readable |
| --- | --- | --- | --- |
| Database and structure | HW4-DB-01, HW4-STRUCTURE-01 | yes | yes |
| Schema | HW4-SCHEMA-01, HW4-SCHEMA-02, HW4-SCHEMA-03 | yes | yes |
| Auth | HW4-AUTH-01 through HW4-AUTH-04 | yes | yes |
| CRUD and Postman | HW4-CRUD-AUTH-01, HW4-CRUD-PERSISTENCE-01, HW4-POSTMAN-POST, HW4-POSTMAN-GET-ALL, HW4-POSTMAN-GET-ID, HW4-POSTMAN-PUT, HW4-POSTMAN-DELETE | yes | yes |
| React | HW4-REACT-LOGIN-REQUIRED, HW4-REACT-ROUTE-GUARD, HW4-REACT-LOGIN, HW4-REACT-CREATE, HW4-REACT-HOME, HW4-REACT-UPDATE, HW4-REACT-AFTER-UPDATE, HW4-REACT-DELETE, HW4-REACT-AFTER-DELETE | yes | yes |
| Seed and N+1 | HW4-SEED-01, naive and fixed shots for page sizes 10, 50, and 200 | yes | yes |
| Benchmark | HW4-BENCHMARK-01, HW4-BENCHMARK-RAW-01 | yes | yes |
| Index | HW4-INDEX-BEFORE, HW4-INDEX-AFTER | yes | yes |
| RAG | HW4-RAG-SETUP-01, retrieval Q1-Q3 and Q4-Q6, compare Q1-Q3 and Q4-Q6, HW4-RAG-CONTEXT-01, HW4-RAG-K-SWEEP, HW4-RAG-EVALUATION | yes | yes |

## Raw evidence coverage

| File | Required count | Result |
| --- | --- | --- |
| nplus1_runs.json | 180 records, 30 in each of 6 groups | pass |
| nplus1_runs.csv | 180 data rows, 30 in each of 6 groups | pass |
| nplus1_summary.json | measured_requests 180 | pass |
| explain_before.json and explain_after.json | parse | pass |
| rag_comparison.json and rag_comparison.csv | 18 rows | pass |
| rag_evaluation.json and rag_evaluation.csv | 18 rows | pass |
| rag_k_sweep.json | 3 runs at k = 1, 3, 5 | pass |
| rag_retrievals.json and rag_retrieval_check.json | parse | pass |
| RAG_ANALYSIS.md | 300-500 words | 484 words |
| Context q5 and q6 | exact refusal sentence | pass |

Database smoke, without reseeding: `s0686_rel`, 5000 rental listings, 200 listing notes, at least one user, 0 orphan notes, index `idx_rental_listings_property_title` present.

## Verifier

`reports/hw04/verification.json` records homework 4, sid4 0686, and verify_seed 260686. `tested_commit` is the HEAD recorded when `verify_hw04.py` runs. overall_pass is true only when the checks pass.

## Remaining items

- report.pdf
- commit of verification.json
- tag hw4
- submission PDF copy/name
