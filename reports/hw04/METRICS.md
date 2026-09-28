# HW4 Metrics

Database: s0686_rel
Primary table: rental_listings
Primary field: property_title
Secondary field: location
Related table: listing_notes

Part 3 benchmark. 30 real HTTP requests per configuration. 180 total. Percentiles are from the unrounded latency values.

| Page size | Version | SQL stmts/req | p50 (ms) | p95 (ms) | p99 (ms) |
| --- | --- | --- | --- | --- | --- |
| 10 | naive | 11 | 5.218 | 7.052 | 7.764 |
| 10 | fixed | 2 | 4.472 | 5.060 | 5.152 |
| 50 | naive | 51 | 10.207 | 16.280 | 34.034 |
| 50 | fixed | 2 | 3.881 | 4.478 | 4.860 |
| 200 | naive | 201 | 28.555 | 29.074 | 34.661 |
| 200 | fixed | 2 | 5.432 | 6.266 | 13.400 |

| Page size | Median speed-up | Median latency reduction |
| --- | --- | --- |
| 10 | 1.167x | 14.298% |
| 50 | 2.630x | 61.975% |
| 200 | 5.257x | 80.977% |

Index `idx_rental_listings_property_title` on `rental_listings(property_title)`.

Query:

```sql
SELECT id, property_title, location
FROM rental_listings
WHERE property_title = 'Rental Listing 2500';
```

| EXPLAIN field | Before index | After index |
| --- | --- | --- |
| type | ALL | ref |
| possible_keys | NULL | idx_rental_listings_property_title |
| key | NULL | idx_rental_listings_property_title |
| rows | 4980 | 1 |
| filtered | 10.0 | 100.0 |
| Extra | Using where | NULL |

Part 4 retrieval setup. No answers were generated.

Documents: 6
Chunks: 415
Chunk size: 500
Overlap: 50
Embedding model: sentence-transformers/all-MiniLM-L6-v2
Embedding dimension: 384
Top-k: 3

| Question | Category | Top-3 sources | Expected source found? |
| --- | --- | --- | --- |
| q1 | one_chunk | ftc_rental_listing_scams.html | Yes |
| q2 | two_chunks | california_tenants_2026.pdf | No. California guide only. FTC data spotlight was not in the top 3. |
| q3 | similar_across_documents | cfpb_tenant_background_market_report.pdf, cfpb_tenant_background_consumer_snapshot.pdf | Yes for the two CFPB reports. HUD guidance was not in the top 3. |
| q4 | ambiguous | hud_rental_screening_guidance.pdf | Yes for HUD guidance. The question is broad, and the CFPB reports were not in the top 3. |
| q5 | not_in_documents | california_tenants_2026.pdf | Not applicable / unsupported question |
| q6 | unrelated | cfpb_tenant_background_market_report.pdf, california_tenants_2026.pdf | Not applicable / unsupported question |
