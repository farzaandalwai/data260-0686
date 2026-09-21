# HW3 Metrics

Embedding model: sentence-transformers/all-MiniLM-L6-v2
Top-k: 5
Seed: 686

## Retrieval Comparison

| Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@5 cosine | Recall@5 | Mean retrieval latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| TokenTextSplitter | 839 | 1042.78 | 0.673236 | 0.645124 | 1.0 | 12.14 |
| SemanticSplitterNodeParser | 286 | 2676.38 | 0.575736 | 0.565879 | 1.0 | 7.48 |
| SentenceWindowNodeParser | 5538 | 138.22 | 0.747511 | 0.646602 | 1.0 | 47.62 |

Avg chunk length is the mean character length of every chunk produced by that chunker.
Top-1 cosine is the mean rank-1 cosine similarity across the five questions.
Mean@5 cosine is the mean cosine similarity of all retrieved top-5 chunks.
Recall@5 is the share of the five questions whose expected source file appears in the top 5 retrieved chunks.

## Confidently Scored Wrong Retrieval

- Technique: SemanticSplitterNodeParser
- Question: q3
- Expected source: hud_rental_screening_guidance.pdf
- Retrieved source: cfpb_tenant_background_market_report.pdf
- Rank: 2
- Store score: 0.723941
- Cosine similarity: 0.708351
- Preview: 1344. 119 MLRI, “Evicted for Life,” supra note 112, p. 4-8. 120 Elora Raymond et al., “Corporate Landlords, Institutional Investors, and Displacement: Eviction Rates in Single- Family Rentals,” Federal Reserve Bank of Atlanta, December 2016
