# AI use

1. I used ChatGPT/Codex to read and explain the HW8 instructions, plan the evidence, write the Kafka implementation and verification scripts, debug failures, operate my Mac, and collect the screenshots. I supplied the assignment, repository, and constraints. The assistant performed most of the implementation, execution, and screenshot collection; I am responsible for reviewing the submission.

2. The first implementation assumed concurrent SQLite journal initialization would work and that every line read from a live JSONL file was complete. Real runs exposed a database-lock error and a JSON parsing error. The first startup also exposed transient Kafka topic-metadata errors. An initial regression check expected a list, but the existing MySQL endpoint correctly returned a paginated object; the check was corrected after reading its real implementation.

3. These were detected from the actual container tracebacks and experiment console output. The fixes were checked by rerunning the complete Kafka experiments and the objective smoke checks, comparing offsets, correlation IDs, UUIDs, retry counts, and all 20 ordering records with the saved raw evidence.

4. The shared database now uses short transactions without changing journal mode during concurrent startup. The live-log reader waits for a newline before parsing the last record. Separate per-process logs avoid concurrent host/container appends losing records. Consumers continue through metadata errors. The final tests use persistent correlation-ID records for pipeline side effects, manual offset commits after processing, three poison attempts followed by a dead letter, and an entity key for ordered related messages.
