# HW7 screenshot manifest

Every image below was captured from the real local application or VS Code terminal on this Mac. Terminal images show `Farzaan Dalwai — DATA 260 HW7`, a real command, output, and a timestamp. The report places each image immediately below its matching short snippet.

| Screenshot | Exact assignment requirement proved | Report section |
| --- | --- | --- |
| `01_ruff_failure.png` | Part 1: actual Ruff lint failure before fixing code | Part 1 — Ruff failure |
| `02_ruff_success.png` | Part 1: Ruff passes after the real fix | Part 1 — Ruff fixed |
| `03_bike_member_ui.jpg` | Part 4: browser upload, 500-row frequent-rider scenario, Buy Monthly Membership, costs, weekly statistics, pricing URL/access/SHA, steps/time/stop | Part 4 — Frequent rider |
| `04_bike_member_timeline.jpg` | Part 4: visible ReAct tool-call and observation timeline for the frequent-rider run | Part 4 — Tool timeline |
| `05_bike_sparse_ui.jpg` | Earlier real sparse-rider browser run; retained as raw evidence, not repeated in the revised PDF | Raw evidence only |
| `05b_sparse_live_full.png` | Part 4: new live sparse-rider browser run; three complementary cropped regions show the 500-row scenario, Pay Per Ride/Minute, both costs, pricing URL/access/SHA, weekly values, six steps/time/success, and the complete four-tool timeline | Part 4 — Sparse rider, decision/source/stop and two side-by-side tool timeline captures |
| `06_official_pricing.jpg` | Part 4: real official Divvy pricing page showing $1 + $0.20/min, $143.90/year, and 45-minute classic-bike allowance | Part 4 — Official prices |
| `07_auth_statuses.png` | Part 1: real HTTP 200, 201, 401, 403 for login, missing/invalid/expired JWT, reader/writer/moderator role cases, without a full token | Part 1 — JWT and role checks |
| `07b_invalid_token_401.png` | Part 1: separate live `curl -i` request to `/auth/me` using an invalid token, showing HTTP 401 and invalid-or-expired response in the VS Code terminal | Part 1 — Separate invalid-token 401 |
| `08_agent_tasks.png` | Part 2: fixed A/B/C multi-tool tasks, real calls, and graceful nonexistent ID | Part 2 — Tool agent |
| `08b_reliability.png` | Part 2: 20 same-settings attempts, verifier count, tool-call total, repair rate and required failure categories | Part 2 — Reliability |
| `09_reflexion.png` | Part 3: failed then retried trace, budgeted probe, verifier result and final success | Part 3 — Reflexion |
| `10_injection_matrix.png` | Part 5: three attacks by three defense conditions and honest outcomes, including blocked SQL gate probe | Part 5 — Injection tests |
| `11_sandbox.png` | Earlier aggregate sandbox run; retained as raw evidence, not repeated in the revised PDF | Raw evidence only |
| `11_sandbox_details.png` | Part 6: timestamped combined live VS Code terminal run showing three globbed Python files, both DEBUG matches, actual alpha.py read content, five named allowed commands and five named blocked commands with reasons | Part 6 — Command gate and ten cases, following six file-tool excerpts |
| `12_verification.png` | Final: live 31/31 verification across auth, agent, CSV, safety and API | Final checks |
| `13_commit_hook.png` | Part 1: Ruff pre-commit hook visibly passed during real commit `2f266c9` in the VS Code terminal | Part 1 — Commit hook |

The three sparse-rider report crops come from different regions of the same full-page screenshot, not separate or reconstructed runs. The member screenshots were captured after the final metadata display was added. The separate invalid-token and detailed sandbox screenshots were captured from the real VS Code terminal with name, command, real output, and timestamp visible. Raw traces and source snapshots identify the corresponding executions.
