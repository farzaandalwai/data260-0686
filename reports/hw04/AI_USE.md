# AI Use

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT throughout the homework to help understand concepts or instructions that I was unsure about. I used ChatGPT for coding help and code debugging when needed. I used ChatGPT to help interpret the homework requirements and understand what screenshots and evidence I needed to capture. I also used ChatGPT to help work through concepts and implementation issues as they came up. I personally ran the code, tested the application, captured the screenshots, and checked the actual outputs and results.

## 2. Give one AI-produced output that was wrong or unsuitable, or one result you independently verified.

I checked the Context RAG answer for the ambiguous screening question against the chunks that were actually retrieved. Two fair-housing sentences were labeled [1] even though they are in the chunk labeled [2], and the refusal sentence was still printed after the bullets. I also checked question 2. The FTC loss page was not in the top five at k = 1, 3, or 5.

## 3. How did you detect the problem or verify the result?

I compared the saved answer with the selected chunks in the comparison file and with the retrieval output on my machine. The extra refusal sentence was still in the answer, and the FTC file name was missing from the question 2 hits. I also counted the N+1 raw file and matched the latency table to the summary file.

## 4. What did you change and why does it work now?

I did not rewrite that model answer by hand. The claims are in the selected chunks, so the faithfulness score stays true. The wrong citation labels and the extra refusal sentence keep the format score false. The question 2 miss stays in the results because that FTC page was never retrieved.
