# AI Use

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT mainly to help me understand the homework requirements, explain parts of the HTML, JavaScript, and Python code, and help me debug some issues while building the agent pipeline. I also used it to understand what results and screenshots I needed to include in the report. I still ran all of the code myself, tested the Ollama model locally, collected the screenshots, ran the experiments, and checked that the final outputs matched the homework requirements.

## 2. Give one AI-produced output that was wrong or unsuitable, or one result you independently verified.

One thing I independently verified was that the agent pipeline always returned exactly 3 tags and a summary of no more than 25 words. I did not want to rely only on the Planner and Reviewer prompts because an LLM can still sometimes return output that does not perfectly follow the requested format.

## 3. How did you detect or verify the problem?

I checked the actual Planner, Reviewer, and Finalized outputs from my local Ollama runs. I also looked at the final JSON and counted the tags and summary words to make sure the output followed the assignment requirements.

## 4. What did you change, and why does it work now?

I kept a separate finalization step that takes only the first 3 tags and limits the summary to 25 words if it is too long. This means that even if the Planner or Reviewer returns extra tags or a longer summary, the final published output still follows the required format.