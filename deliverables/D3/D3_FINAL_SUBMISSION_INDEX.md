# D3 Final Submission Index

This file is the submission map for the D3 package. The old D4/final-demo/tuning work is merged into this D3 submission; do **not** create or submit a separate D4 folder unless the instructor explicitly asks for it.

## What to submit

Submit the repository/folder containing these core paths:

- `notebooks/`
- `src/`
- `configs/`
- `data/gold/`
- `data/metadata/papers_metadata.csv`
- `data/metadata/findings_metadata.csv`
- `data/tuning/finetune_qa.jsonl`
- `reports/`
- `models/qlora_adapter/`
- `deliverables/D3/`
- `README.md`
- `requirements.txt`

Do **not** submit local secrets:

- `.env`
- Neo4j credential text files
- API keys in screenshots or notebook output

## Member-by-member evidence map

| Member | Main notebook | Responsibility | Main proof file(s) |
|---|---|---|---|
| Reem | `notebooks/D3_01_Reem_page_citation_verification.ipynb` | Page/citation verification and data quality | `reports/tables/page_citation_check.csv`, `reports/member_sections/reem_d3_data_quality_section.md` |
| Salma | `notebooks/D3_02_Salma_retrieval_ablation.ipynb` | Retrieval ablation and latency comparison | `reports/tables/d3_retrieval_ablation.csv`, `reports/tables/d3_retrieval_ablation_summary.csv`, `reports/member2_d3_retrieval_ablation_section.md` |
| Rana | `notebooks/D3_03_Rana_graphrag_executor.ipynb` | GraphRAG executor, Cypher subgraph selection, graph-to-chunk expansion, citations | `reports/tables/d3_graph_guided_results.csv`, `reports/member3_d3_graphrag_executor_section.md` |
| Aaya | `notebooks/D3_04_Aaya_online_graphrag_adaptation_v2.ipynb` | Static vs topic-gated vs feedback-adaptive GraphRAG | `reports/tables/d3_online_retrieval_comparison.csv`, `reports/tables/d3_online_retrieval_per_query.csv`, `reports/tables/d3_online_feedback_events.csv`, `reports/member_sections/aaya_d3_adaptation_section.md` |
| Alia | `notebooks/D3_05_Alia_safety_rag_evaluation.ipynb` | Safety, citation verifier, faithfulness/relevance evaluation | `reports/tables/d3_safety_before_after.csv`, `reports/tables/d3_rag_eval_metrics.csv`, `reports/member_sections/alia_d3_safety_eval_section.md` |
| All / final scope | `notebooks/D3_06_Final_Demo_Tuning_Merged_Scope.ipynb`, `notebooks/D3_07_Kaggle_QLoRA_Tuning.ipynb` | PEFT/QLoRA and final-demo/tuning evidence | `data/tuning/finetune_qa.jsonl`, `models/qlora_adapter/`, `reports/tables/d3_or_final_zero_shot_vs_tuned.csv`, `reports/tables/d3_tuning_latency.csv` |
| Merged final latency scope | `notebooks/D4_02_Salma_retrieval_latency.ipynb` | Retrieval latency/cache evidence included in D3 final scope | `reports/tables/d4_retrieval_latency.csv`, `reports/tables/d4_retrieval_latency_summary.csv` |

## Final key evidence

- Gold Q/A set: `data/gold/d3_gold_qa.csv` — 15 curated evidence-grounded questions.
- Graph findings: `data/metadata/findings_metadata.csv` — 15 D3 gold-derived page-anchored `Finding` rows.
- GraphRAG result table: `reports/tables/d3_graph_guided_results.csv` — 6 query demonstrations with graph hits/chunks/citations.
- Online adaptation result: `reports/tables/d3_online_retrieval_comparison.csv` — static/topic-gated/adaptive comparison over 15 rows.
- PEFT/QLoRA result: `reports/tables/d3_or_final_zero_shot_vs_tuned.csv` — zero-shot vs tuned adapter comparison.
- Adapter: `models/qlora_adapter/` — trained QLoRA adapter files.
- Run card: `configs/d3_run_card.yaml`.
- Final checklist: `deliverables/D3/D3_ACCEPTANCE_CHECKLIST.md`.

## Known execution note

Gemini quota was unstable during final preparation. Saved outputs are kept. Do not rerun Gemini-heavy cells unless quota is available. The code now supports stable mock-prompt output for graph execution, so GraphRAG/Cypher/citation evidence remains runnable without Gemini answer generation.
