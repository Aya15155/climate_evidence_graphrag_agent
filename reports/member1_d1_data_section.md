# Member 1 D1 Section — Dataset and Proxy Benchmark

For D1, I prepared the retrieval data foundation for the Climate Evidence GraphRAG Agent.

## Corpus

- 300 open-access climate-related PDFs
- 49,541 extracted page-aware chunks
- metadata CSV with document IDs, titles, authors, venues, year, PDF paths, topics, countries, regions, sectors, technologies, policies, targets, and indicators

## Benchmark repair

The first automatically generated retrieval set was preserved as:

```text
data/gold/d1_retrieval_eval_set_legacy_autogen.json
```

During D1 verification we found that some of its question labels were not truly anchored to the page named in the question. To avoid reporting misleading retrieval scores, I prepared a repaired page-grounded proxy benchmark:

```text
data/gold/d1_retrieval_eval_set.json
```

The repaired set contains 120 questions generated from exact source pages and is rebuilt by:

```bash
python scripts/build_d1_proxy_eval_set.py
```

Each item keeps page evidence, source-document IDs, and relevant chunk IDs for the target page. Because the set is still automatically generated, every row remains marked `needs_manual_review=true`.

## Why this matters for D1

The repaired benchmark gives the AutoML experiment a more honest supervised signal and avoids inflated or misleading results from the earlier draft labels. It is suitable for D1 comparison, while a manually reviewed benchmark should replace it in later deliverables.

