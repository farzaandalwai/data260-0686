# HW9 measured results

## Initial authenticated ingress run (threshold 0.85)
Requests: 12; hits: 8; hit rate: 66.67%.
Mean hit latency: 30.521 ms; mean miss latency: 1665.960 ms.
Wrong returned answers: 4; cache speed alone is not correctness.
Latency is measured inside the handler, including embedding, Redis search, version lookup, and (on misses) Kafka/local-model work; it excludes HTTP authentication overhead.

## Threshold sweep

| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |
|---|---|---|---|---|
| 0.75 | 75.0% | 25.0% | 285.023 | 210 |
| 0.80 | 75.0% | 25.0% | 283.669 | 210 |
| 0.85 | 75.0% | 25.0% | 282.772 | 210 |
| 0.90 | 55.0% | 7.5% | 523.583 | 78 |
| 0.95 | 25.0% | 0.0% | 865.898 | 30 |

False-hit rate = wrong cached answers / 40. Costs were fixed before the sweep: miss=1 and false-hit/support=20 normalized units; total=misses+20*false_hits, not measured dollars. Each threshold starts from the same ten real warm-up answers; case misses do not populate that frozen benchmark cache. Normal ingress does populate misses.

## Four independent held-out variants

| Variant | Correct | Incorrect | Mean attempts | Mean latency (ms) |
|---|---|---|---|---|
| Baseline | 6 | 2 | 1.000 | 775.715 |
| Evaluator Repair | 8 | 0 | 1.250 | 670.357 |
| Lesson Memory | 7 | 1 | 1.125 | 697.720 |
| Validated Improvement | 7 | 1 | 1.125 | 638.623 |

Proposed lesson validation: 6/6 before, 5/6 after; accepted=False. The rejected extra lesson is not shipped. Validated Improvement therefore retains the prior lesson only. Memory is not claimed to beat Evaluator Repair.
The no-memory controlled examples ended REVISE after two attempts. A separate training-only, memory-assisted controlled example repaired the deliberately omitted value and ended PASS at attempt two; no held-out input or answer was changed to obtain this demonstration.

## Data integrity

The original 5,000 rental records have the same checksum after restoring the staleness experiment. The new view counter was also restored to zero after the 25-access demonstration. Database backups are private under .hw9_runtime/backups/ and are not committed.
