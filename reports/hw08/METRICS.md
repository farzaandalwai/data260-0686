# HW8 measured results

Final experiment run: `hw8-e66681cbf8`. VERIFY_SEED: 260686. Sources: `raw/failure_results.json`, `raw/ordering_input.json`, and both ordering CSV files. Before-fix consumers are deliberately unsafe experimental baselines, not application services.

| Failure scenario | Before fix | After fix |
|---|---|---|
| Duplicate delivery | 2 effects for one correlation ID. | 1 draft; replay skipped. CREATE replay returned the same UUID. |
| Consumer killed mid-work | Early commit 57; source offset 56; 0 original effects. | Offset 62 received twice; committed stayed 62 at kill and became 63 after completion. |
| Poison message | 5 observed retries before stopping; later message blocked. | 3 attempts, s0686_dead_letter, later message completed. |
| Two partitions/two consumers | Unkeyed: 20 completions across partitions 0 and 1; completion order differed from send order. | Entity key rental-0686: all 20 in partition 0, completed 1 through 20. |

## Unkeyed
- Count: 20
- Partitions: [0, 1]
- Active processing instances: ['writer-1', 'writer-2']
- Completion order: [2, 4, 6, 8, 1, 10, 3, 12, 5, 14, 7, 16, 9, 18, 11, 20, 13, 15, 17, 19]
- Matches send order: False

## Keyed
- Count: 20
- Partitions: [0]
- Active processing instances: ['writer-1']
- Completion order: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
- Matches send order: True

Two group members held one task partition each. Unkeyed messages were deliberately distributed round-robin without a key, with seeded payloads/delays. In the keyed run, one Writer owned the entity's single partition while the other remained in the group. This measures completion order and does not imply Kafka reorders records within a partition.

The entity dictionary/cache is process-local. The pipeline's SQLite cache survives Writer restart, but an output publish/mark-sent crash window can still cause downstream duplicate delivery; downstream stages also deduplicate. No end-to-end exactly-once claim is made.
