# D3 Final Audit Summary

Audit mode: static file/output validation plus selected non-Gemini notebook execution. Gemini-heavy cells were not rerun during finalization.

## Final artifact status

- Required D3 notebooks are present and JSON-valid.
- Required output CSV/JSON/JSONL files are present and readable.
- Rana GraphRAG notebook was cleaned of old hardcoded Neo4j credentials and rerun in stable no-Gemini answer mode.
- Neo4j graph evidence is available through Aura/local `.env` configuration.
- PEFT/QLoRA adapter files are present under `models/qlora_adapter/`.
- Old D4 retrieval-latency evidence is included as merged D3/final-scope evidence.

## Final counts from audited outputs

| Evidence | Value |
|---|---:|
| D3 gold Q/A rows | 15 |
| D3 findings metadata rows | 15 |
| Neo4j graph nodes used in final run | 552 |
| Neo4j Finding nodes used in final run | 15 |
| Online GraphRAG per-query rows | 45 |
| Online methods compared | 3 |
| Safety before/after rows | 5 |
| RAG metric rows | 8 |
| QLoRA tuning rows | 15 |
| QLoRA training duration | 133.31 sec |
| Retrieval cache median speedup | 22.2x |

## Submission caution

Do not include `.env` or downloaded Neo4j credential files in the submitted package. The repository should include `.env.example` only.
