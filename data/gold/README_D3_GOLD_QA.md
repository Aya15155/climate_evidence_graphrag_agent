# D3 Gold Q/A Set

The D3 gold evaluation file is:

`data/gold/d3_gold_qa.csv`

It contains 15 evidence-grounded questions created from Reem-verified valid citation chunks in:

`reports/tables/page_citation_check.csv`

## How to use it

Use this file as the shared answer key for D3:

- Salma: retrieval ablation.
- Rana: GraphRAG executor evaluation.
- Aaya: online/adaptive GraphRAG comparison.
- Alia: safety, faithfulness, citation correctness, and tuning evaluation.
- Reem: citation/page verification.

## Important rule

Each gold row points to a real chunk in:

`data/sample/sample_chunks.json`

and each selected chunk was marked `valid` in Reem's page citation check.

## Compatibility columns

The file intentionally includes duplicate-compatible column names because different notebooks expect different schemas:

- `query_id` and `question_id`
- `question` and `query`
- `gold_document_id`, `relevant_doc_id`, and `relevant_document_id`
- `gold_chunk_id` and `relevant_chunk_ids`
- `topic` and `true_topic`

Do not remove these duplicate columns unless all notebooks are updated together.

## Question vs retrieval query

The file has both:

- `question` - human-readable question for the report and presentation.
- `query` / `retrieval_query` - exact-retrieval wording with distinctive evidence terms.

This is intentional. D3 evaluates exact chunk retrieval, which is stricter than document-level retrieval. The `retrieval_query` wording makes the target chunk findable without giving the model the answer or the gold chunk ID.

Current diagnostic:

- 15 / 15 gold chunks are in BM25 top-5 using `retrieval_query`.
- The diagnostic table is `reports/tables/d3_gold_exact_chunk_bm25_rank_diagnostic.csv`.
