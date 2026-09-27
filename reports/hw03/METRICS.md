# HW3 Metrics

Embedding model: sentence-transformers/all-MiniLM-L6-v2
Top-k: 5
Seed: 686

## Retrieval Comparison

| Chunker | Nodes | Recall@5 | Mean latency (ms) |
|---|---:|---:|---:|
| token | 839 | 1.0 | 11.35 |
| semantic | 286 | 1.0 | 6.99 |
| sentence_window | 5538 | 1.0 | 46.73 |

Recall@5 is the share of the five questions whose expected source file appears in the top 5 retrieved chunks.

## Confidently Scored Wrong Retrieval

- Chunker: semantic
- Question: q3
- Expected source: hud_rental_screening_guidance.pdf
- Retrieved source: cfpb_tenant_background_market_report.pdf
- Rank: 2
- Store score: 0.723941
- Cosine similarity: 0.708351
- Preview: 1344. 119 MLRI, “Evicted for Life,” supra note 112, p. 4-8. 120 Elora Raymond et al., “Corporate Landlords, Institutional Investors, and Displacement: Eviction Rates in Single- Family Rentals,” Federal Reserve Bank of Atlanta, December 2016
