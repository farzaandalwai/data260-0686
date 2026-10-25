# HW7 metrics

All values below come from the JSON files in `raw/`. The 20 baseline trials used `llama3.2:latest`, temperature 0, and the same three fixed prompts in A/B/C rotation. “Verified” means the deterministic evidence checker passed, not merely that the model returned text.

## Hand-written agent and Reflexion

| Measure | Baseline (20 independent trials) | Reflexion (3 fixed tasks) |
| --- | ---: | ---: |
| Verified task successes | 13/20 (65%) | 3/3 (100%) |
| Unsupported-claim failures | 7/20 (35%) | 1 failed attempt, corrected on retry; 0 final |
| Retry rate | 0/20 | 1/3 tasks retried (2 retry attempts) |
| Tool calls | 66 total; 3.30/trial | 18 total; 6.00/task |
| Input + output tokens | 43,050 total; 2,152.5/trial | 15,159 total; 5,053/task |
| Latency | 95.10 s total; 4.75 s/trial | 26.50 s total; 8.83 s/task |
| Verifier false rejections | 0 observed | 0 observed |

Task A was verified 0/7 at baseline because the model called a limited three-row search result the total number of listings. B was 7/7; C was 6/6. The model made 66 well-formed tool calls before repair and 66 after repair (100% both); no repairs were needed. Recorded malformed arguments, unknown tools, text-when-tool-required, schema failures, and lost chains were each 0. The missing-ID test returned a graceful not-found answer. Reflexion A needed two retries; the first unsupported claim was rejected, the second attempt did not complete, and the third passed. B and C passed first try. A separate tight-step probe produced a real `budget_exhausted` first attempt and a successful second attempt; it is not counted in the three-task comparison.

## Divvy framework agent

| Scenario | CSV rows | Selected rides in sample month | Pay/use sample month | Pay/use projected year | Annual membership billed upfront | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Frequent rider | 500 | 48 | $130.99 | $1,571.88 | $143.90 | Buy Monthly Membership |
| Sparse rider | 500 | 3 | $6.51 | $78.12 | $143.90 | Pay Per Ride/Minute |

Both scenarios completed four tool calls and returned `success`. The membership is actually billed annually; $11.99/month is only a comparison equivalent, not a monthly charge. These are modeled rider selections from distinct 500-row samples of genuine public January 2026 Divvy trips, not 500 trips by one person. The CSV and pricing source metadata, access timestamp, and SHA-256 are in `raw/divvy_sources.json`.

## Injection and sandbox

The local nine-case injection fixture found one wrong recommendation before defenses, one with prompt defense alone, and zero with prompt plus final cost/tool enforcement. It did not persuade the model to issue a non-SELECT query or contaminate the answer in any of the three conditions. The separate SQL gate probe denied the hostile DELETE fixture. These zeroes are observations, not claims that the attacks are impossible.

The sandbox found two DEBUG matches across three temporary Python files. Five safe commands were allowed and executed; five risky commands were blocked. The final live smoke test passed 31/31 checks (`verification.json`).
