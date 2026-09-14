# HW2 Metrics

## Schema Validation - 30 Runs

| Outcome | Count | Mean latency (ms) |
|---|---:|---:|
| Valid first attempt | 30 | 2848.47 |
| Valid after 1 retry | 0 | N/A |
| Valid after 2+ retries | 0 | N/A |
| Hit turn ceiling | 0 | N/A |

## Turn Ceiling Comparison

| Ceiling | Runs | Completion Rate | Mean Latency (ms) |
|---:|---:|---:|---:|
| 2 | 20 | 100.0% | 2793.19 |
| 10 | 20 | 100.0% | 3916.19 |

Ceiling 2 is selected for deployment because completion rates matched and it had lower mean latency.

## Adversarial Test

- Total runs: 5
- Ceiling used: 2
- Runs that hit the ceiling: 0
- Observed rate: 0.0%
- Why difficult: The rental text contains formatting instructions that conflict with the required schema.
- Proposed fix: Clearly separate untrusted listing content from the model's output instructions.
