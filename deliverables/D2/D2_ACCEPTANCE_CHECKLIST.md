# D2 Acceptance Checklist

## Whole-team notebook rule
- [x] `notebooks/D2_retrieval_graph_build.ipynb` is executed with visible outputs.
- [x] Each member notebook is executed with visible outputs.
- [x] No member notebook is template-only or unfinished.
- [x] `.py` modules are used as support code, not as the only evidence.

## Reem - ingestion/data
- [x] `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` completed.
- [x] PDF/document count shown.
- [x] Chunk count shown.
- [x] Metadata completeness checked.
- [x] Page-map/provenance examples inspected.

## Salma - retrieval
- [x] `notebooks/D2_02_Salma_retrieval_comparison.ipynb` completed.
- [x] BM25-only, dense-only, and hybrid compared.
- [x] Hit@5/Recall-style metric and p95 latency reported.
- [x] NDCG@5 and MRR reported.
- [x] Top-k examples include document/page provenance.

## Rana - graph
- [x] `notebooks/D2_03_Rana_graph_build_cypher.ipynb` completed.
- [x] Neo4j node/relationship counts shown.
- [x] 3-5 meaningful Cypher queries with outputs.
- [x] Graph is climate-specific, not only generic paper metadata.

## Aaya - online/adaptation
- [x] `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` completed.
- [x] River learner connected to retrieval routing/adaptive fusion.
- [x] Static retrieval compared with topic-gated/adaptive retrieval.
- [x] Drift/feedback limitation explained.

## Alia - API/tests/integration
- [x] `notebooks/D2_05_Alia_api_tests_integration.ipynb` completed.
- [x] `/search` endpoint returns results with document/page provenance.
- [x] pytest smoke tests pass: 4 passed.
- [x] README/run steps verified in notebook evidence.

## Remaining limitations to disclose
- [x] MongoDB and Qdrant Docker services are configured; local notebook/API path uses files + cached dense matrix for reproducibility when stores are not running.
- [x] Some graph finding evidence is curated/metadata-grounded; stronger extraction can be expanded in D3.
