# AI use

1. I used ChatGPT to read and understand the HW9 instructions, clarify what each part required, and plan screenshots after the runs. I also used AI for code and debugging. I wrote much of the implementation, ran many checks, and captured screenshots through my Mac; I reviewed the results and requested revisions.

2. The initial Redis parsing assumed RESP2, but the installed client returned RESP3. This produced a KeyError that the first HTTP wrapper incorrectly presented as a missing listing. The local model also initially omitted listing_id from JSON answers. An initial console tee ran before its output directory existed; the actual setup JSON and private backups were retained.

3. These problems were detected from real HTTP responses, the direct traceback, and saved model output. After fixing the protocol and output schema, the requests were rerun. The 40 labels were committed before measurements and remained unchanged. Database checksums, Redis metadata, actual Kafka correlation IDs, per-case records, validation results, and the unchanged held-out test hash were checked against the recorded outputs.

4. The Redis client now explicitly uses RESP2, and missing-listing errors have their own exception. The existing local adapter accepts a JSON schema so the cache path requires all response keys without forcing their values. The cache uses a transactional data version and a measured threshold choice. Validation rejected the proposed extra lesson because it regressed one case. Earlier no-memory controlled repairs still failed at the two-attempt limit; a later training-only example with the saved lesson repaired successfully. The report keeps those outcomes and does not claim lessons always improve answers.
