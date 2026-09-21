# AI Use

## 1. What did you use an AI assistant for and what did you do yourself?

I used an AI assistant mainly to help me understand the homework requirements, explain concepts while I was working, debug code when I ran into issues, and figure out what screenshots and evidence were needed for the report. I ran the application, tested the authentication flow, ran the retrieval experiments, collected the screenshots, and verified the outputs myself.

## 2. Give one AI-produced output that was wrong/unsuitable, or one thing you independently verified.

One thing I independently verified was the average chunk-length calculation. The first version calculated the average using only the retrieved top-5 chunks instead of all chunks produced by each chunking technique.

## 3. How did you detect the problem or verify the result?

I checked the calculation against the homework instructions and noticed that the assignment asked for the average length of all chunks produced by each chunker. I then reviewed how the metric was being calculated and confirmed that it needed to use the full set of chunks.

## 4. What did you change and why does it work now?

I changed the calculation so that average chunk length is computed across every node produced by each chunking technique. The corrected values were saved in chunk_stats.json, and the summary script now uses those full-index statistics when generating the final metrics table.
