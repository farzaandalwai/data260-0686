# AI Use

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT mainly to help me understand the code, and in some places to help write and debug code. I also used it to understand what exactly I needed to include in the report as evidence, and to check if the screenshots I took were good enough to include in the report. I still went through the code myself, ran everything, checked the outputs, and made sure the requirements were actually working.

## 2. Give one AI-produced output that was wrong or unsuitable, or one result you independently verified.

One thing that was wrong at first was how the loop safety was being counted. The `turn_count` was increasing every time the supervisor ran, which would make a ceiling like 2 not really make sense because even a normal Planner → Reviewer run goes through the supervisor multiple times.

## 3. How did you detect or verify the problem?

I noticed it when I looked at the actual graph flow and the streamed output. A normal run already had the supervisor showing up multiple times, so I realized using that count for the retry ceiling would not really represent how many times the Planner was actually retrying.

## 4. What did you change, and why does it work now?

I changed it by adding a separate `planner_attempts` counter. Now it only increases when the Planner actually runs. This makes the ceiling actually mean the maximum number of Planner attempts, and it also makes sure the graph can stop instead of looping forever.