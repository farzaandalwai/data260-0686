# HW6 Memory-Cost Metrics

Model: `llama3.2:latest` at temperature 0.0
Embedding: `sentence-transformers/all-MiniLM-L6-v2` (local, 384 dimensions)
Component token counts: MiniLM WordPiece estimates; total prompt/completion counts are exact Ollama counts.
Each condition used one isolated 30-turn run followed by the same five probes.
Part 4 file memory was disabled in every condition so it could not distort the MongoDB window comparison.

## Required comparison

| Setting | Mean prompt tokens/turn | Mean completion tokens/turn | Mean latency (ms) | Probe quality (1-5) | Runs/turns |
|---|---:|---:|---:|---:|---:|
| SHORT_TERM_N=4 | 601.667 | 96.000 | 3389.011 | 4.200 | 1 / 30 + 5 probes |
| SHORT_TERM_N=12 | 988.367 | 96.000 | 5059.893 | 5.000 | 1 / 30 + 5 probes |
| SHORT_TERM_N=30 | 1632.233 | 96.000 | 6843.770 | 5.000 | 1 / 30 + 5 probes |
| relevance_aware_eviction | 969.867 | 96.000 | 5731.379 | 5.000 | 1 / 30 + 5 probes |

## Relevance-aware eviction versus SHORT_TERM_N=30

- Absolute prompt-token savings: 662.366 tokens/turn
- Percentage prompt-token savings: 40.580%
- Probe-quality change: +0.000 points
- Latency change: -1112.391 ms

## Cost estimate for 10,000 x 30-turn conversations

| Setting | Input cost | Output cost | Total cost |
|---|---:|---:|---:|
| SHORT_TERM_N=4 | $180.5001 | $144.0000 | $324.5001 |
| SHORT_TERM_N=12 | $296.5101 | $144.0000 | $440.5101 |
| SHORT_TERM_N=30 | $489.6699 | $144.0000 | $633.6699 |
| relevance_aware_eviction | $290.9601 | $144.0000 | $434.9601 |

## Selection rule

Best is the lowest projected-cost configuration within 0.5 points of the highest probe score. Worst is the highest-cost configuration in that same quality band; if none share the band, it is the objectively lowest-quality configuration.

Best: **relevance_aware_eviction**. Worst: **SHORT_TERM_N=30**.
