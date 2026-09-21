# DATA-260 Homework 1

## Student Configuration

- SID4: 0686
- PORT_BASE: 8686
- PREFIX: s0686
- SEED: 686
- VERIFY_SEED: 260686
- DOMAIN_ID: 6
- Assigned Domain: Rental Housing Listings
- Python: 3.11
- Local Model: llama3.2:latest

I used `llama3.2:latest` instead of the recommended `qwen3:8b` because it is a smaller local model that runs on my hardware.

---

# Part 1 - Rental Housing Listing Web Application

The web application contains a rental housing listing form with:

- Property title
- Location
- Submitter email
- Property description
- Property type
- Terms and conditions checkbox
- Submit button

The JavaScript validates that the description contains more than 25 characters and that the terms checkbox is selected.

After a successful submission, the form data is converted to JSON and logged to the browser console. Object destructuring, the spread operator, and a closure are also used as required.

## Run Locally with Docker

Build the Docker image:

```bash
docker build -t data260-0686 .
```

Run the container using my assigned port:

```bash
docker run --rm -p 8686:80 data260-0686
```

Open the application in a browser:

```text
http://localhost:8686
```

The same application was also deployed using AWS ECS with one Fargate task.

---

# Part 2 - Agentic AI

Part 2 uses two agents:

1. Planner
2. Reviewer

A finalization step produces the final JSON output.

The Planner creates exactly three tags and a summary of no more than 25 words. The Reviewer checks the result, and the finalizer produces the final output.

## Run Part 2

```bash
python3.11 agents_demo.py \
  --title "Spacious 3 Bedroom House in San Jose" \
  --content "Three bedroom rental house with a swimming pool, air conditioning, garage parking, and a large backyard near downtown San Jose." \
  --temperature 0.0
```

Example final tags:

- San Jose Rental
- Pool House
- Family Home

Example final summary:

```text
Spacious 3 bedroom house with pool, AC, garage parking and large backyard near downtown San Jose.
```

---

# Part 3 - Measuring Non-Determinism

The fixed experiment input is stored in:

```text
reports/hw01/cases/nondeterminism_input.json
```

The same input is used for all runs.

The experiment performs:

- 20 runs at temperature 0.7
- 20 runs at temperature 0.0
- 40 runs total

## Run Part 3

```bash
python3.11 part3_experiment.py
```

The raw experiment results are saved to:

```text
reports/hw01/raw/part3_runs.json
reports/hw01/raw/part3_runs.csv
```

The calculated metrics are saved to:

```text
reports/hw01/METRICS.md
```

The metrics include:

- Number of distinct tag sets
- Tags appearing in all 20 runs
- Tags appearing in exactly one run
- Latency p50
- Latency p95
- Latency p99

In my experiment, temperature 0.7 produced more variation between runs, while temperature 0.0 produced the same tag set across all 20 runs.

Two users providing the same input at a higher temperature may receive different but related tags. This type of variation can be acceptable for creative tagging, but it may not be acceptable for tasks that require consistent classifications or decisions.

---

# Part 4 - Model Client and Token Accounting

The reusable Ollama model adapter is located at:

```text
src/model_client.py
```

The command-line client is:

```text
hw1_client.py
```

The model behavior instructions are stored in:

```text
AGENT.md
```

The model is instructed to perform code reviews using bullet points only.

## Run Part 4

```bash
python3.11 hw1_client.py
```

The client supports:

```text
/stats
```

to display:

- Turn count
- Cumulative input tokens
- Cumulative output tokens
- Conversation history length

Use:

```text
/exit
```

to stop the program.

A five-turn conversation was completed, with `/stats` recorded after turn 3 and turn 5.

Per-turn token counts are saved in:

```text
reports/hw01/raw/part4_tokens.json
```

## Why is prior conversation context resent with every turn?

The model does not automatically remember previous API requests. Earlier messages must be included again so that the model has the conversation context needed to answer the newest request.

## How is a system prompt different from a user message?

A system prompt provides overall instructions for how the model should behave. A user message contains the actual request or information the user wants the model to respond to.

## Why do input tokens grow over a conversation?

Input tokens increase because previous user and assistant messages are included again in later requests as conversation history.

## What eventually limits that growth?

The model has a maximum context window. When the conversation becomes too large, older information must eventually be removed, summarized, or otherwise reduced.

---

# Verification

A simple verification script checks that the required Homework 1 files exist.

Run:

```bash
python3.11 verify_hw01.py
```

Successful verification should include:

```json
{
  "passed": true
}
```

The complete verification result is stored in:

```text
reports/hw01/verification.json
```

---

# Homework Output Files

Homework results are stored under:

```text
reports/hw01/
```

Important files include:

```text
reports/hw01/RUN_LOG.txt
reports/hw01/METRICS.md
reports/hw01/AI_USE.md
reports/hw01/verification.json
reports/Report.pdf
reports/hw01/cases/nondeterminism_input.json
reports/hw01/raw/part3_runs.json
reports/hw01/raw/part3_runs.csv
reports/hw01/raw/part4_tokens.json
```

---

# Reproducing the Homework

Part 1:

```bash
docker build -t data260-0686 .
docker run --rm -p 8686:80 data260-0686
```

Part 2:

```bash
python3.11 agents_demo.py \
  --title "Spacious 3 Bedroom House in San Jose" \
  --content "Three bedroom rental house with a swimming pool, air conditioning, garage parking, and a large backyard near downtown San Jose." \
  --temperature 0.0
```

Part 3:

```bash
python3.11 part3_experiment.py
```

Part 4:

```bash
python3.11 hw1_client.py
```

Verification:

```bash
python3.11 verify_hw01.py
```

---

# Homework 2

Homework 2 extends the rental listing project with FastAPI, LangGraph, Pydantic validation, and loop-safety experiments.

## Reproduce Homework 2

Install dependencies:

```bash
python3.11 -m pip install -r requirements.txt
```

Start Ollama and make sure the documented local model is available:

```bash
ollama serve
ollama pull llama3.2:latest
```

Start the FastAPI application:

```bash
python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8686
```

Open `http://localhost:8686`.

Run the agent graph:

```bash
python3.11 agent_graph.py
```

Run the Part 4 experiments:

```bash
python3.11 part4_experiment.py
```

Run final verification:

```bash
python3.11 verify_hw02.py
```

---

## Homework 3

HW3 continues using the same FastAPI application. The application will run on port 8686.

Personal configuration:

- SID4: 0686
- PORT_BASE: 8686
- PREFIX: s0686
- SEED: 686
- VERIFY_SEED: 260686
- DOMAIN_ID: 6
- DOMAIN: Rental Housing Listings
