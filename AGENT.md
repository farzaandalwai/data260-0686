# DATA 260 Rental Housing Assistant Instructions

1. Project description: extend the existing rental-housing application; do not create a second application or replace prior homework behavior.
2. Technology stack: use Python 3.11, FastAPI, MySQL for the existing relational APIs, MongoDB `s0686_doc` for HW6 documents and memory, React/Vite for the existing client, and local Ollama only.
3. Coding convention: write small functions with descriptive snake_case names, type hints, concise docstrings, and timezone-aware UTC timestamps.
4. Coding convention: validate external input at boundaries and return safe errors that never reveal credentials, cookies, password hashes, or connection strings.
5. Testing approach: add objective checks for success and failure paths, clean up only test-owned records, and preserve reproducible seeds and raw evidence.
6. Testing approach: run regression checks for the existing FastAPI, MySQL, React, and MCP behavior before submission.
7. Prohibited action: never call a paid or hosted model API; model replies and embeddings must remain local.
8. Prohibited action: never delete or rewrite existing MySQL rental data, prior homework reports, or unrelated working-tree changes.
9. Prohibited action: never accept arbitrary filesystem paths from chat commands; file memory is limited to root `AGENT.md` and `MEMORY.md`.
