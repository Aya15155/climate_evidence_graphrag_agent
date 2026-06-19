# D3 Acceptance Checklist

## Required by original D3 brief

- [ ] GraphRAG executor chooses a subgraph by Cypher.
- [ ] Executor expands from graph nodes to supporting chunks.
- [ ] Executor blends graph-supported chunks with hybrid retrieval.
- [ ] Executor answers with citations and page ranges.
- [ ] Small gold Q/A set exists and is used for evaluation.
- [ ] Faithfulness and answer-relevance scores are reported.
- [ ] p95 latency is reported.
- [ ] At least one safety mitigation is implemented.
- [ ] Safety before/after evidence is shown.
- [ ] Ablation compares vector-only vs graph-guided vs hybrid quality/latency.

## Required PEFT/QLoRA and final-demo scope

- [ ] PEFT/QLoRA tuning requirement confirmed as included in D3.
- [ ] Tuning card completed with dataset size, epochs, learning rate, LoRA rank/alpha/dropout, quantization, hardware/time, and license notes.
- [ ] Zero-shot vs tuned comparison completed, or zero-shot baseline plus honest hardware/time non-feasibility note if training cannot run.
- [ ] Final demo questions prepared.
- [ ] README one-command setup verified.
- [ ] pytest smoke tests pass.
- [ ] Final report includes architecture, experiments, ablations, failure cases, ethics/licensing, and future work.

## Evidence files expected

- [ ] `data/gold/d3_gold_qa.csv`
- [ ] `reports/tables/page_citation_check.csv`
- [ ] `reports/tables/d3_retrieval_ablation.csv`
- [ ] `reports/tables/d3_graph_guided_results.csv`
- [ ] `reports/tables/d3_online_retrieval_comparison.csv`
- [ ] `reports/tables/d3_safety_before_after.csv`
- [ ] `reports/tables/d3_rag_eval_metrics.csv`

- [ ] `reports/tables/d3_or_final_zero_shot_vs_tuned.csv`
- [ ] `data/tuning/finetune_qa.jsonl`
- [ ] `reports/tables/d3_tuning_latency.csv`