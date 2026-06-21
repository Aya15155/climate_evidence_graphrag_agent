# D3 Final Acceptance Checklist — GraphRAG, Evaluation, Safety, and Merged Final Scope

Status: **finalized for submission**  
Scope note: the original D4/final-demo/PEFT/latency items are treated as **merged D3 scope**. No separate D4 deliverable folder is required.

## Core D3 GraphRAG requirements

- [x] GraphRAG executor chooses a subgraph by Cypher.  
  Evidence: `notebooks/D3_03_Rana_graphrag_executor.ipynb`, `src/rag/graphrag_executor.py`, `src/graph/cypher_queries.py`.
- [x] Executor expands from graph nodes to supporting chunks.  
  Evidence: `reports/tables/d3_graph_guided_results.csv` with `n_graph_chunks` and graph hit columns.
- [x] Executor blends graph-supported chunks with hybrid retrieval.  
  Evidence: `reports/tables/d3_graph_guided_results.csv`, `reports/tables/d3_retrieval_ablation.csv`.
- [x] Executor answers with citations/page ranges.  
  Evidence: `reports/tables/d3_graph_guided_results.csv`, `reports/tables/page_citation_check.csv`.
- [x] Small gold Q/A set exists and is used for evaluation.  
  Evidence: `data/gold/d3_gold_qa.csv` and `data/gold/README_D3_GOLD_QA.md`.
- [x] Faithfulness and answer relevance are reported.  
  Evidence: `reports/tables/d3_rag_eval_metrics.csv`, `reports/tables/d3_or_final_zero_shot_vs_tuned.csv`.
- [x] p95 latency is reported.  
  Evidence: `reports/tables/d3_retrieval_ablation_summary.csv`, `reports/tables/d3_tuning_latency.csv`, `reports/tables/d4_retrieval_latency_summary.csv`.
- [x] Safety mitigation is implemented and evaluated.  
  Evidence: `notebooks/D3_05_Alia_safety_rag_evaluation.ipynb`, `reports/tables/d3_safety_before_after.csv`.
- [x] Ablation compares retrieval variants.  
  Evidence: `notebooks/D3_02_Salma_retrieval_ablation.ipynb`, `reports/tables/d3_retrieval_ablation_summary.csv`.
- [x] Online/adaptive GraphRAG comparison is included.  
  Evidence: `notebooks/D3_04_Aaya_online_graphrag_adaptation_v2.ipynb`, `reports/tables/d3_online_retrieval_comparison.csv`.

## Merged final-scope / old D4 items included in D3

- [x] PEFT/QLoRA tuning included.  
  Evidence: `notebooks/D3_07_Kaggle_QLoRA_Tuning.ipynb`, `models/qlora_adapter/`, `reports/qlora_training_summary.json`.
- [x] Tuning dataset exists.  
  Evidence: `data/tuning/finetune_qa.jsonl` with 15 evidence-grounded rows.
- [x] Zero-shot vs tuned comparison exists.  
  Evidence: `reports/tables/d3_or_final_zero_shot_vs_tuned.csv`.
- [x] Tuning/hardware/latency evidence exists.  
  Evidence: `reports/tables/d3_tuning_latency.csv`.
- [x] Final demo/tuning merged notebook exists.  
  Evidence: `notebooks/D3_06_Final_Demo_Tuning_Merged_Scope.ipynb`.
- [x] Retrieval latency/cache evidence exists as merged final-scope evidence.  
  Evidence: `notebooks/D4_02_Salma_retrieval_latency.ipynb`, `reports/tables/d4_retrieval_latency_summary.csv`.

## Important execution note

Some notebooks contain optional Gemini answer-generation code. For final stability, Rana's GraphRAG notebook and the patched executor support mock/grounded prompt output when Gemini quota fails or is disabled. This does **not** remove the graph retrieval, Cypher, blending, citation, or metric evidence. Do not rerun Gemini-heavy cells unless quota is available.
