# AI use

## 1. What the AI assistant did and what I did

I used Codex to inspect the assignment and existing repository, implement and debug the FastAPI/PyMongo memory system, build objective test and experiment scripts, operate the local applications, organize evidence, and draft the report. I supplied the repository, fixed personal configuration, local services, model, assignment files, authorization boundaries, and review constraints. All reported database records, model replies, metrics, hashes, and screenshots come from commands run on my Mac; no output was invented.

## 2. One unsuitable AI output or independently verified item

The first 30-message-window experiment was unsuitable. Its exact Ollama prompt counts reached about 2,050 tokens and then stayed at that ceiling, so the nominal `SHORT_TERM_N=30` condition had silently lost older prompt content. It misleadingly appeared cheaper than `SHORT_TERM_N=12` and one probe fell to score 1.

## 3. How the issue was detected or verified

I compared the saved per-turn exact `prompt_eval_count` values across conditions. The 30-message condition stopped growing at the model runtime's default context boundary even though more messages were still being added. The invalid aggregate is preserved as `raw/invalid_first_sweep_context_truncation.json` instead of being reported as a valid result.

## 4. What changed and why it now works

The shared Ollama adapter now accepts explicit context and output limits. The final sweep used `num_ctx=16384`, `num_predict=96`, and temperature 0.0 for every condition, with fresh condition-specific user and session IDs. In the corrected run, the 30-message prompt passed the old ceiling and then stabilized only after the 30-message window was full. The final raw files and report use only this corrected sweep.
