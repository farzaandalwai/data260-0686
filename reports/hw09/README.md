# HW9 rental cache and two agents

This extends the existing app, MySQL s0686_rel records, local model adapter, and actual HW8 Kafka Planner/Writer/Reviewer. No demo SQLite users, hosted API, second app, or decorative UI is used. Configuration remains SID4 0686, port 8686, prefix s0686, seed 686, verify seed 260686, domain 6.

## Run

Use the ignored local .env for the existing MySQL and JWT settings. Install Redis/PyYAML in the existing Python 3.11 environment. Run the private backup/migration before starting the new ORM model. The script preserves rental rows and adds view_count plus a one-row s0686_cache_version table.

```sh
uv pip install --python .venv-hw7/bin/python -r requirements-hw08.txt redis==8.1.0 PyYAML
.venv-hw7/bin/python -m scripts.hw9_setup
docker compose -f compose.hw08.yml -f compose.hw09.yml build fastapi
docker compose -f compose.hw08.yml -f compose.hw09.yml up -d kafka redis
bash scripts/hw8_topics.sh
docker compose -f compose.hw08.yml -f compose.hw09.yml up -d worker fastapi planner writer reviewer
export HW8_RAW_DIR=reports/hw09/raw/kafka
.venv-hw7/bin/python run_hw9_cache.py counter
.venv-hw7/bin/python run_hw9_cache.py requests
.venv-hw7/bin/python run_hw9_cache.py sweep
.venv-hw7/bin/python run_hw9_cache.py stale
.venv-hw7/bin/python run_hw9_agents.py
.venv-hw7/bin/python -m scripts.hw9_repair_with_memory
.venv-hw7/bin/python verify_hw09.py
.venv-hw7/bin/python -m scripts.hw9_metrics
```

The existing send_question.py has an optional --cache path through POST /api/hw9/ask; its default uncached HW8 behavior remains available. The new endpoint uses existing JWT authentication. Use HW9_TOKEN from the existing login flow; never print or commit it. The request demo creates and removes only a temporary test reader and explicitly evaluates 0.85; ordinary requests use hw9_cache_config.json. A threshold override is available for authenticated experiments.

```sh
.venv-hw7/bin/python send_question.py 'What is the listing code for rental listing 1?' --cache --listing-id 1 --field listing_code
```

## Experiment integrity

cache_cases.yaml is JSON-compatible YAML containing exactly 40 labeled cases. Its original commit is 0cdc5328e78881f95f5756247ba0ee95c55162a6, before embedding measurements or sweeps. The generator is for initial setup only; do not rerun it after measurements. See EXPERIMENT_PLAN.md for the fixed setup and preselected cost assumptions. The sweep uses a separate Redis namespace for each threshold and the same ten warm-up answers from real pipeline misses; case misses are not added to that frozen benchmark cache. Every miss still calls the real Kafka pipeline/local adapter.

Part 4 uses a separate factual snapshot, input-only training/validation/test JSON files, and independent memory copies for each variant. The held-out data is first loaded after lesson selection and is not changed between variants. The extra candidate was rejected after validation regressed from 6/6 to 5/6. The later controlled repair uses training data, not a test case. Model errors remain in the actual results.

## Invalidation and limits

Every Redis key and index starts with s0686. No FLUSHDB is used. The view counter syncs only every ten increments, so loss of Redis can lose up to nine unsynced views. GREATEST prevents an older sync from lowering the persisted count. The demo restores its counter and deletes only that new test counter key.

The data-version row is updated in the same MySQL transaction as ordinary listing API writes. Cache lookups read that version and store it in Redis metadata; old versions cannot match the vector query. Out-of-band SQL must call invalidate_data explicitly, as shown by the stale-answer experiment. A global version invalidates unrelated entries too and adds a database read to cache hits. Redis entries expire after an hour. This homework cache does not guarantee safety for unseen numeric identifiers: threshold 0.95 had zero false hits in these 40 cases, not a universal correctness guarantee.

The counter/staleness tests restore original fields in finally blocks. All 5,000 original rental fields have the same checksum. Backups contain private database data, are chmod 600, and stay under ignored .hw9_runtime/backups/. Unrelated working-tree changes and earlier reports are not staged.

## Submission hash

A tracked PDF cannot contain the hash of the commit that contains it without changing that hash. The tracked report uses the symbolic hw9 tag reference. After committing and tagging the reviewed state, export reports/hw09/submission/Dalwai_HW9.pdf with the resolved hash and run verify_hw09.py --tag hw9 --output reports/hw09/submission/verification.json. These post-tag artifacts are published on the same repository's hw9 release; the submission directory is ignored so publication does not alter the tagged source. Tracked verification is explicitly the pre-commit source-hash snapshot.

References: [Redis vector index documentation](https://redis.io/docs/latest/develop/ai/search-and-query/vectors/) and [Ollama structured outputs](https://ollama.com/blog/structured-outputs).
