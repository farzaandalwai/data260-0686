# HW8 Kafka rental listings

This extends the existing FastAPI application in `main.py`; HW1-HW7 routes and the React client remain in place. The request worker uses the established listing form fields from `Domain_schema.md`. Its exercise IDs are UUIDs, independent of the existing MySQL numeric IDs.

## Run

Use the existing local `.env` for MySQL/JWT settings. It is ignored by Git and excluded from the Docker build. Ports are bound to localhost.

```sh
docker compose -f compose.hw08.yml build fastapi
docker compose -f compose.hw08.yml up -d kafka
bash scripts/hw8_topics.sh
docker compose -f compose.hw08.yml up -d worker fastapi planner writer reviewer
uv pip install --python .venv-hw7/bin/python -r requirements-hw08.txt
.venv-hw7/bin/python homework_demo.py
.venv-hw7/bin/python send_question.py --model
.venv-hw7/bin/python run_hw8_experiments.py
.venv-hw7/bin/python verify_hw08.py
```

The experiments intentionally stop and kill only this homework's Writer. The `scripts/hw8_baseline.py` consumer is deliberately unsafe and is used only for measured before-fix cases. It is not an application service.

## Messages

The request service uses exactly `s0686_entity_requests` and `s0686_entity_responses`.

```json
{"correlation_id":"one UUID per request","reply_to":"s0686_entity_responses","operation":"GET_LISTING","data":{"listing_id":"worker-generated UUID"}}
```

Replies contain the same `correlation_id`, a Boolean `success`, and either `listing_id`, `listing`, or a clean `error`. The API is `POST /api/hw8/listings`; it accepts an optional caller correlation ID and preserves it, or the client creates it once. The only allowed reply topic is the required response topic.

Planner reads `s0686_inbox`, Writer reads `s0686_tasks` (two partitions), and Reviewer reads `s0686_drafts` and sends `s0686_final`. Each runs in a separate container/process. Both Writers use the `s0686_writer` group. Final JSON contains `status`, `answer`, and `correlation_id`. A real journey uses local Ollama through the existing adapter; failure/order tests use facts-only replies to isolate Kafka behavior from model timing.

## Limits

The entity dictionary and its duplicate-response cache survive duplicate delivery while that worker runs, but not a worker restart. The pipeline's local SQLite cache survives Writer restart; its primary key counts each correlation ID once per stage. A crash between publishing and marking a cached response as sent can publish it again, so downstream stages also deduplicate. This is not a claim of end-to-end exactly-once delivery. Kafka container recreation loses this exercise broker's storage; the tests kill/restart Writer, not the broker. This single-node, replication-factor-one setup is for local homework.

Unkeyed ordering deliberately uses round-robin partition selection with no key so both partitions are exercised. The same seeded payloads and delays are then sent with the same entity key, letting Kafka select their one partition. Reported order is measured completion order, not a simulated schedule.

JMeter's attached direct-user demo uses a different entity and port. It is a supplemental reference, not a Part 1-3 submit item in the controlling HW8 PDF, so it is not copied into this rental service.

References: [Apache Kafka Docker quickstart](https://kafka.apache.org/41/getting-started/docker/) and [Confluent Python client API](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html).

## Final hash and tagged verification

A Git commit cannot contain its own hash in a tracked report without changing that hash. The tracked PDF and verification JSON are the reviewed pre-tag snapshots, with source hashes identifying the tested application. After the final reviewed commit is tagged `hw8`, run the verifier with `--tag hw8 --output reports/hw08/submission/verification.json` and export the submission PDF with `--tagged-commit "$(git rev-parse 'hw8^{commit}')" --output reports/hw08/submission/Dalwai_HW8.pdf`. The submission directory is ignored so resolving the actual hash does not modify the tagged source. The resolved PDF and tagged verification are published as assets on the repository's `hw8` release, alongside the source tag: https://github.com/farzaandalwai/data260-0686/releases/tag/hw8.
