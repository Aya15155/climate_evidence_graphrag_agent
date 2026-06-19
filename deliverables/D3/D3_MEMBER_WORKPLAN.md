# D3 Member Workplan ? GraphRAG Executor, Evaluation, Safety, and Final Scope

This folder is the planning/evidence hub for the upcoming D3 deliverable.

## Important scope note

The original project brief lists D3 and D4 separately. Since PEFT/QLoRA tuning is included in this D3 submission, then D3 must cover:

1. GraphRAG executor, evaluation, safety, and ablation.
2. Required final-demo/tuning/repo-hygiene requirements from the old D4 section.

Confirm the merged scope with the doctor before doing expensive PEFT/QLoRA work.

## Member ownership

| Member | Notebook | Main responsibility | Main evidence file(s) |
|---|---|---|---|
| Reem | `notebooks/D3_01_Reem_page_citation_verification.ipynb` | Page citation verification and data-quality impact | `reports/tables/page_citation_check.csv` |
| Salma | `notebooks/D3_02_Salma_retrieval_ablation.ipynb` | Vector-only vs hybrid vs graph-guided retrieval ablation | `reports/tables/d3_retrieval_ablation.csv` |
| Rana | `notebooks/D3_03_Rana_graphrag_executor.ipynb` | GraphRAG executor: Cypher subgraph, chunk expansion, answer citations | `reports/tables/d3_graph_guided_results.csv` |
| Aaya | `notebooks/D3_04_Aaya_online_graphrag_adaptation.ipynb` | Static vs topic-gated/adaptive retrieval inside GraphRAG | `reports/tables/d3_online_retrieval_comparison.csv` |
| Alia | `notebooks/D3_05_Alia_safety_rag_evaluation.ipynb` | Safety mitigation, citation verifier, faithfulness/relevance metrics | `reports/tables/d3_safety_before_after.csv`, `reports/tables/d3_rag_eval_metrics.csv` |
| All | `notebooks/D3_graphrag_eval_safety.ipynb` | Combined final evidence notebook | All D3 tables |
| All/required | `notebooks/D3_06_Final_Demo_Tuning_Merged_Scope.ipynb` | Required PEFT/QLoRA/final-demo scope in D3 | tuning card, zero-shot vs tuned, demo checklist |

## Submission principle

Every member should implement their own part, run it, paste results/errors into their AI chat, ask why the design works or fails, and commit their own changes.

## Required PEFT/QLoRA tuning outputs

- `data/tuning/finetune_qa.jsonl` - evidence-grounded tuning Q/A rows with document/page references.
- `reports/tables/d3_or_final_zero_shot_vs_tuned.csv` - zero-shot vs tuned comparison, or zero-shot baseline plus honest non-feasibility note if training cannot run.
- `reports/tables/d3_tuning_latency.csv` - tuning/final model latency evidence.
