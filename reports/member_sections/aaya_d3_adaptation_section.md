# Aaya D3 Contribution — Online Adaptation inside GraphRAG

## Scope

My D3 contribution extends the D2 online retrieval work into the GraphRAG pipeline by comparing three retrieval modes:

1. **static_graphrag** — fixed BM25/dense retrieval weights.
2. **topic_gated_graphrag** — topic-based routing profiles from the online topic prediction layer.
3. **feedback_adaptive_graphrag** — River topic prediction plus FeedbackAdapter updates to adjust the retrieval policy over the query stream.

The adaptive component changes the BM25/dense retrieval policy inside the GraphRAG executor. It does not claim to learn new Cypher templates or graph traversal actions.

## Evaluation status

- Run mode: `final`
- Evaluation status: `final_d3_gold_run`
- Topic accuracy basis: `gold_true_topic_only`
- PEFT/QLoRA status: `trained_adapter_compared`
- Rows per method: `15`

If the evaluation status is partial, the results should be treated as limited evidence rather than a complete final gold-set evaluation.

## Main results

| Method | strict_chunk_recall@5 | strict_chunk_ndcg@5 | strict_chunk_mrr@5 | document_recall@5 | document_ndcg@5 | document_mrr@5 | page_window_recall@5 | faithfulness | answer_relevance | citation_correctness | citation_hit_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| static_graphrag | 0.8000 | 0.8000 | 0.8000 | 0.9333 | 0.8977 | 0.9000 | 0.8667 | 0.6794 | 0.7085 | 0.9333 | 1.0000 |
| topic_gated_graphrag | 0.8000 | 0.8000 | 0.8000 | 0.9333 | 0.8977 | 0.9000 | 0.8667 | 0.6794 | 0.7085 | 0.9333 | 1.0000 |
| feedback_adaptive_graphrag | 0.8000 | 0.8000 | 0.8000 | 0.9333 | 0.8977 | 0.9000 | 0.8667 | 0.6794 | 0.7085 | 0.9333 | 1.0000 |

## Interpretation

The feedback-adaptive run matched the static baseline on the measured quality metrics. Therefore, no improvement is claimed.

The helps/hurts analysis shows that feedback-adaptive GraphRAG helped `0` queries and hurt `0` queries compared with the static GraphRAG baseline.

## Metric explanation

Strict chunk-level retrieval is the hardest metric because it only gives credit when GraphRAG retrieves the exact gold chunk ID. Document-level and page-window relevance are also reported because GraphRAG may retrieve evidence from the correct document or page while not matching the exact annotated chunk ID. Soft overlap metrics are used only as diagnostics and are not reported as gold relevance.

## PEFT/QLoRA status

PEFT/QLoRA status is recorded as `trained_adapter_compared`. If tuned output files are unavailable, the notebook does not fabricate a zero-shot vs tuned comparison.

## Limitation

The feedback signal is topic-level and therefore coarse. It can indicate whether an adaptive retrieval policy was useful, but it does not identify whether an error came from BM25 retrieval, dense retrieval, graph expansion, citation selection, or answer generation. Direct graph-query adaptation would require learning graph-specific actions such as relation filters, hop depth, entity constraints, or template selection.
