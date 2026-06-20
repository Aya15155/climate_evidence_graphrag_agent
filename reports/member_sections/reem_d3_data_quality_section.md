## Reem — D3 Page Citation Verification and Data Quality

### Method

Page citation verification was implemented in `src/ingest/page_verifier.py` and run over
two input sets: (1) all 42 chunk_id citations found in the 6 GraphRAG answer rows from
`reports/tables/d3_graph_guided_results.csv`, and (2) a random sample of 150 real chunks
from `data/sample/sample_chunks.json`. Each citation was assigned one of five status labels:
`valid`, `weak_overlap`, `text_not_found`, `missing_page`, or `missing_document`.
Verification applied a metadata check first (document_id in papers_metadata, page <= total_pages),
then a text-quality check (chunk text >= 200 chars for full confidence).

### Results

Of 187 citations verified, 145 (77.5%) were `valid`, 5 (2.7%) were `weak_overlap`,
8 (4.3%) were `text_not_found`, and 29 (15.5%) were `missing_document`. No `missing_page`
cases were found, confirming the base corpus page maps are internally consistent.
All 29 `missing_document` and all 8 `text_not_found` cases originated from the GraphRAG
executor's synthetic graph-node chunk IDs, which do not correspond to real extracted chunks.

### Limitation

The verifier checks text length, not semantic faithfulness. A citation can be labelled
`valid` even if the retrieved text does not actually support the claim in the answer.
Full faithfulness verification would require embedding-based or LLM-based claim-grounding
against the cited page text, which is outside the scope of this check.
Additionally, scanned PDFs with no extractable text would produce false `text_not_found`
labels for otherwise correct citations.

### Safety implication

Any answer that cites a chunk_id not found in the verified corpus must be flagged as
ungrounded. Source-pinning (D3 Alia) should refuse or warn on such answers. The GraphRAG
executor (D3 Rana) should resolve all chunk references to real corpus IDs before
constructing the final answer.
