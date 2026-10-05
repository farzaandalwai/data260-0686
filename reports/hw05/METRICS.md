# HW5 metrics

## Part 3 retry experiment

These numbers are the measured final-call outcomes after the retry policy. They are not first-attempt success rates. The run used seed 260686, a 0.75 second timeout, at most 3 attempts, and backoff of 0.02 seconds then 0.04 seconds, capped at 0.08 seconds. Each rate used 50 calls.

| Injected failure rate | Final success rate | Mean latency (ms) | p99 latency (ms) |
| --- | --- | --- | --- |
| 0% | 100% (50/50) | 2.447 | 48.166 |
| 20% | 100% (50/50) | 7.800 | 27.767 |
| 50% | 94% (47/50) | 19.881 | 72.002 |

At 20% injected failure, retries recovered every call in this seeded run, so the final success rate was 50/50. At 50%, three calls still failed after all three attempts were used. Mean latency rose with the injected failure rate because failed attempts sleep before the next try. The p99 values are not strictly ordered: the 0% p99 is higher than the 20% p99 because of an individual timing outlier.

These latencies stay well under a second, including the p99 values, so the same short timeout and three attempts are suitable for an interactive request. Batch work can use more attempts, a somewhat longer timeout, and a longer backoff, because waiting longer is less of a problem when a person is not waiting on the response.

## Part 5 agent scenarios

Real runs used local `llama3.2:latest`. The first four attempts, logged at 13:28, stopped with `model_error` because the model put the tool name in `action`. A 13:29 rerun completed, but some final answers added facts that were not in the tool result. After the prompt was told to use only returned fields, the corrected runs below were appended at 14:06. Earlier records were kept. Step count is the number of harness steps. Tool-call count is how many times `execute_tool` ran.

| Scenario | User input | Steps | Stop reason | Tool calls | Logged at |
| --- | --- | --- | --- | --- | --- |
| search | Find a few rental listings in San Jose. | 2 | normal_completion | 1 | 2026-10-05T14:06:17-07:00 |
| detail | Show me details for rental listing 1. | 2 | normal_completion | 1 | 2026-10-05T14:06:19-07:00 |
| aggregate | Summarize the listings managed by manager 1. | 2 | normal_completion | 1 | 2026-10-05T14:06:20-07:00 |
| multi_step | Find rental listings in San Jose and then give me details for one of them. | 3 | normal_completion | 2 | 2026-10-05T14:06:24-07:00 |

The corrected search answer says 1 available unit for each returned listing. The corrected detail answer says Milpitas, CA and 1 unit, and it does not add a street address. The aggregate answer uses listing_count 5000 and total_available_units 5000. The multi-step run called `search_listings` and then `detail_lookup` for listing 5. No live safety block was attempted, because these seeded listings have available units above zero. The unavailable-listing rule was checked with the offline fixture instead.
