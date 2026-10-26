# AI use

1. I used ChatGPT to read and understand the HW7 instructions, clarify what each part required, and plan screenshots after the runs. I also used AI for code and debugging. I wrote much of the implementation, ran many checks, and captured screenshots through my Mac; I reviewed the results and requested revisions.

2. One unsuitable AI-produced result was the local model's recommendation to pay per ride when the supplied yearly pay-per-use cost was $2,160 and the annual membership was $143.90. Another issue found during evidence checking was wording that treated a three-row limited search as the total number of San Jose listings.

3. The pricing error was found by comparing the returned decision with the two actual costs. The listing-count error was found by checking the search limit and tool observations against the answer. AI-assisted terminal and browser runs checked the 31-check smoke test, real Ruff hook, both UI scenarios, and safety-gate tests; I reviewed the saved evidence.

4. The implementation added a deterministic cost check at the final answer boundary and a verifier rule that rejects claims of a total count from a limited search. The tool-side SQL gate independently rejects non-SELECT statements. The corrected outputs are grounded in the saved CSV, official Divvy pricing snapshot, and real rental-tool observations.
