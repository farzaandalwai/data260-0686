# HW7 metrics

All values below come from the JSON files in `raw/`. The 20 baseline trials used `llama3.2:latest`, temperature 0, and the same three fixed prompts in A/B/C rotation. “Verified” means the deterministic evidence checker passed, not merely that the model returned text.

## Twenty-attempt baseline reliability

| Measure | Before repair | After repair |
| --- | ---: | ---: |
| Well-formed tool calls | 66/66 (100%) | 66/66 (100%) |
| Malformed arguments | 0 | 0 |
| Unknown tool | 0 | 0 |
| Text when a tool was required | 0 | 0 |
| Schema failures | 0 | 0 |
| Lost multi-step chain | 0 | 0 |

The verifier passed 13/20 complete tasks. No tool-call repair was needed. Task A was verified 0/7 because the model called a limited three-row search result the total number of listings; B was 7/7 and C was 6/6. The missing-ID test returned a graceful not-found answer.

## Original versus Reflexion on the same A/B/C tasks

| Measure | Original A/B/C first attempts | Reflexion A/B/C |
| --- | ---: | ---: |
| Verified task successes | 2/3 (66.7%) | 3/3 (100%) |
| Unsupported claims in final answers | 1/3 | 0/3; one failed attempt corrected |
| Retry rate | 0/3 | 1/3 tasks (2 retry attempts) |
| Tool calls | 10 total; 3.33/task | 18 total; 6.00/task |
| Input + output tokens | 6,586 total; 2,195.33/task | 15,159 total; 5,053/task |
| Latency (ms) | 15,000.17 total; 5,000.06/task | 26,504.18 total; 8,834.73/task |
| Verifier false rejections | 0 observed | 0 observed |

The original column uses attempts 1–3 of `part2_attempts.json`, matching the fixed A/B/C prompts in `part3_reflexion.json`. Reflexion A needed two retries; the first unsupported claim was rejected, the second attempt did not complete, and the third passed. B and C passed first try. A separate tight-step probe produced a real `budget_exhausted` first attempt and a successful second attempt; it is not counted in the three-task comparison. No false rejection was observed in these cases; this does not establish a general false-rejection rate.

## Divvy framework agent

| Scenario | CSV rows | Selected rides in sample month | Pay/use sample month | Pay/use projected year | Annual membership billed upfront | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Frequent rider | 500 | 48 | $130.99 | $1,571.88 | $143.90 | Buy Monthly Membership |
| Sparse rider | 500 | 3 | $6.51 | $78.12 | $143.90 | Pay Per Ride/Minute |

Both scenarios completed four tool calls and returned `success`. The membership is actually billed annually; $11.99/month is only a comparison equivalent, not a monthly charge. These are modeled rider selections from distinct 500-row samples of genuine public January 2026 Divvy trips, not 500 trips by one person. The CSV and pricing source metadata, access timestamp, and SHA-256 are in `raw/divvy_sources.json`.

## Injection and sandbox

The local nine-case injection fixture found one wrong recommendation before defenses, one with prompt defense alone, and zero with prompt plus final cost/tool enforcement. It did not persuade the model to issue a non-SELECT query or contaminate the answer in any of the three conditions. The separate SQL gate probe denied the hostile DELETE fixture. These zeroes are observations, not claims that the attacks are impossible.

The sandbox found two DEBUG matches across three temporary Python files. Five safe commands were allowed and executed; five risky commands were blocked. The final live smoke test passed 31/31 checks (`verification.json`).
