# D2 Acceptance Checklist

## Whole-team notebook rule
- [ ] `notebooks/D2_retrieval_graph_build.ipynb` is executed with visible outputs.
- [ ] Each member notebook is executed with visible outputs.
- [ ] No TODO-only notebook is submitted as finished work.
- [ ] `.py` modules are used as support code, not as the only evidence.

## Reem - ingestion/data
- [ ] `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` completed.
- [ ] PDF/document count shown.
- [ ] Chunk count shown.
- [ ] Metadata completeness checked.
- [ ] Page-map/provenance examples inspected.

## Salma - retrieval
- [ ] `notebooks/D2_02_Salma_retrieval_comparison.ipynb` completed.
- [ ] BM25-only, dense-only, and hybrid compared.
- [ ] Recall@5 and p95 latency reported.
- [ ] NDCG@5 or MRR reported where labels allow it.
- [ ] Top-k examples include document/page provenance.

## Rana - graph
- [ ] `notebooks/D2_03_Rana_graph_build_cypher.ipynb` completed.
- [ ] Neo4j node/relationship counts shown.
- [ ] 3-5 meaningful Cypher queries with outputs.
- [ ] Graph is climate-specific, not only generic paper metadata.

## Aaya - online/adaptation
- [ ] `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` completed.
- [ ] River learner connected to retrieval routing or adaptive fusion.
- [ ] Static retrieval compared with topic-gated/adaptive retrieval.
- [ ] Drift/feedback limitation explained.

## Alia - API/tests/integration
- [ ] `notebooks/D2_05_Alia_api_tests_integration.ipynb` completed.
- [ ] `/search` endpoint returns results with provenance.
- [ ] pytest smoke tests pass.
- [ ] README run steps verified.
