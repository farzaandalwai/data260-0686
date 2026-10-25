# AI use

1. I used an AI assistant to draft and revise Python, React, test scripts, and this report. I chose the rental-housing domain, checked the provided assignment against my repository, ran the local model and tools, and reviewed the saved evidence and final decisions on my machine.

2. One unsuitable AI-produced result was the local model's recommendation to pay per ride when the supplied yearly pay-per-use cost was $2,160 and the annual membership was $143.90. Another issue I independently caught was wording that treated a three-row limited search as the total number of San Jose listings.

3. I detected the pricing error by comparing the returned decision with the two actual costs. I detected the listing-count error by checking the search limit and tool observations against the answer. I also ran the 31-check smoke test, the real Ruff hook, both UI scenarios, and the safety-gate tests.

4. I added a deterministic cost check at the final answer boundary and a verifier rule that rejects claims of a total count from a limited search. The tool-side SQL gate independently rejects non-SELECT statements. The corrected outputs are grounded in the saved CSV, official Divvy pricing snapshot, and real rental-tool observations.
