# HW8 screenshot manifest

All terminal captures were taken with computer control from the real VS Code terminal on this Mac. Originals are retained unchanged; report images are crops only. Display helpers format saved actual runs, not fabricated output. Every terminal capture includes Farzaan Dalwai, the command, and UTC capture time.

## 01_services.png
- PDF requirement: Part 1 V.1
- Report section: Setup
- Command/evidence: `docker ps; worker ready and FastAPI startup logs`

## 04_client_demo_code.png
- PDF requirement: Part 1 source screenshots
- Report section: Client and demo
- Command/evidence: `nl -ba hw8_kafka.py (85-96); homework_demo.py (7-24)`

## 05_worker_api_code.png
- PDF requirement: Part 1 source screenshots
- Report section: Worker and API
- Command/evidence: `nl -ba hw8_worker.py (27-51); routers/hw8_listings.py (16-23)`

## 16_api.png
- PDF requirement: Part 1 II and V.2-3
- Report section: API response
- Command/evidence: `curl POST /api/hw8/listings with saved listing UUID and caller correlation ID`

## 02_roundtrip.png
- PDF requirement: Part 1 IV and V.2-4
- Report section: CREATE then GET
- Command/evidence: `python show_hw8_evidence.py roundtrip; reads raw/round_trip.json`

## 15_validation.png
- PDF requirement: Part 1 III
- Report section: Validation
- Command/evidence: `python show_hw8_evidence.py checks | head -n 23`

## 03_topics.png
- PDF requirement: Part 2 II
- Report section: Topics
- Command/evidence: `bash scripts/hw8_topics.sh; Kafka CLI create and describe`

## 06_agents.png
- PDF requirement: Part 2 III and Submit code
- Report section: Separate agents
- Command/evidence: `cat planner.py writer.py reviewer.py; docker top each agent`

## 07_journey.png
- PDF requirement: Part 2 IV and Submit journey/final JSON
- Report section: Message journey
- Command/evidence: `python show_hw8_evidence.py journey; reads raw events and agent_journey.json`

## 08_duplicate.png
- PDF requirement: Part 3 I and Submit logs
- Report section: Duplicate delivery
- Command/evidence: `python show_hw8_evidence.py duplicate`

## 09_death.png
- PDF requirement: Part 3 II and Submit logs
- Report section: Consumer death
- Command/evidence: `python show_hw8_evidence.py death`

## 10_poison.png
- PDF requirement: Part 3 III and Submit logs
- Report section: Poison message
- Command/evidence: `python show_hw8_evidence.py poison`

## 11_unkeyed.png
- PDF requirement: Part 3 IV and Submit logs
- Report section: Unkeyed ordering
- Command/evidence: `python show_hw8_evidence.py unkeyed; all 20 raw CSV rows`

## 12_keyed.png
- PDF requirement: Part 3 IV and Submit logs
- Report section: Keyed ordering
- Command/evidence: `python show_hw8_evidence.py keyed; all 20 raw CSV rows`

## 13_verification.png
- PDF requirement: Repository verification.json
- Report section: Verification
- Command/evidence: `python show_hw8_evidence.py checks | tail -n 19`

## Supplemental capture
`originals/14_react.png` is the existing React login-required page inspected in the browser; it is not used as proof of authenticated functionality and is not duplicated in the report.
