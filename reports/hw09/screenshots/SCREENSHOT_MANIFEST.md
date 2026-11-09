# HW9 screenshot manifest

Native Mac computer-control captures from the actual VS Code terminal. Each shows Farzaan Dalwai, the command and UTC capture time. Display helpers explicitly identify saved real runs; the index capture inspects live Redis. Report images are crops only. Originals remain unchanged.

## 01_services.png
- Exact requirement: Inherited repository instructions: working system/configuration
- Report: page 1, Setup
- Command: `docker ps --filter name=s0686-hw8 --format 'table {{.Names}}  {{.Status}}'`

## 02_views.png
- Exact requirement: Part 1: INCR on accesses 1-25; MySQL syncs at 10 and 20
- Report: page 2, Part 1 - Views
- Command: `python show_hw9_evidence.py views`

## 03_index.png
- Exact requirement: Part 2: real Redis vector index and cosine embeddings
- Report: page 3, Part 2 - Vector cache
- Command: `python show_hw9_evidence.py index`

## 04_requests.png
- Exact requirement: Part 2: at least ten requests; flags, scores, latency and measured hit/miss means
- Report: page 4, Part 2 - Requests
- Command: `python show_hw9_evidence.py requests`

## 05_journey.png
- Exact requirement: Part 2: miss uses existing HW8 Kafka/local adapter; hit reuses final answer
- Report: page 5, Part 2 - Pipeline
- Command: `python show_hw9_evidence.py journey`

## 06_labels.png
- Exact requirement: Part 3.1: exactly 40 labels committed before the sweep
- Report: page 6, Part 3.1 - Frozen cases
- Command: `python show_hw9_evidence.py labels`

## 07_thresholds.png
- Exact requirement: Parts 3.2 and 3.4: five thresholds, filled metrics, cost choice
- Report: page 7, Parts 3.2/3.4 - Thresholds
- Command: `python show_hw9_evidence.py thresholds`

## 08_false_hit.png
- Exact requirement: Part 3.3: complete observed false hit
- Report: page 8, Part 3.3 - False hit
- Command: `python show_hw9_evidence.py falsehit`

## 09_stale.png
- Exact requirement: Part 3.5: actual SQL change, stale answer, invalidation and restoration
- Report: page 9, Part 3.5 - Stale answer
- Command: `python show_hw9_evidence.py stale`

## 10_datasets.png
- Exact requirement: Part 4: separate reference facts and input-only train/validation/test datasets
- Report: page 10, Part 4 - Datasets
- Command: `python show_hw9_evidence.py datasets`

## 11_repair.png
- Exact requirement: Part 4.1 / Required demonstration 1 and 3: Answering/Evaluator code, full revision and stop
- Report: page 11, Part 4.1 - Repair
- Command: `python show_hw9_evidence.py repair`

## 12_lessons.png
- Exact requirement: Part 4.2 / Required demonstration 2: all five lesson fields and later reuse
- Report: page 12, Part 4.2 - Lessons
- Command: `python show_hw9_evidence.py lessons`

## 13_validation.png
- Exact requirement: Part 4.3: before/after validation and rejection of regression
- Report: page 13, Part 4.3 - Validation
- Command: `python show_hw9_evidence.py validation`

## 14_variants.png
- Exact requirement: Part 4.4 / Required demonstration 4: independent four-variant test table
- Report: page 14, Part 4.4 - Held-out results
- Command: `python show_hw9_evidence.py variants`

## 15_verification.png
- Exact requirement: Inherited repository instructions: objective checks and earlier-homework regression
- Report: page 15, Verification
- Command: `python show_hw9_evidence.py checks | tail -n 18`
