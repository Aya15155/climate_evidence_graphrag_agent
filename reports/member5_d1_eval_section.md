# Member 5 D1 Section — Evaluation and Report Integration

## Metrics used

The D1 report uses:

- **Recall@5** — whether the correct page-level evidence is recovered in the top five results
- **NDCG@5** — whether relevant evidence is ranked near the top
- **MRR** — where the first relevant result appears
- **p95 latency** — tail retrieval latency

## Final D1 comparison

| System | Recall@5 | NDCG@5 | MRR | p95 latency |
|---|---:|---:|---:|---:|
| Baseline | 0.667 | 0.522 | 0.493 | 674.5 ms |
| AutoML tuned | 0.833 | 0.682 | 0.645 | 676.2 ms |

## Integration checks completed

- AutoML numbers now come from the runnable script rather than placeholder examples.
- The YAML run card matches the generated results table.
- The short report uses only D1-required content: AutoML, online learning, chart, decisions, and pitfalls.
- Later-deliverable graph content was removed from the D1 report so the document stays aligned with the Week 5 brief.

## Remaining limitation

The D1 proxy benchmark is still automatically generated and every item remains flagged for manual review. It is acceptable as a D1 supervised proxy, but a manually reviewed benchmark should be prepared before later deliverables.

