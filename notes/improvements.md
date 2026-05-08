# Notes for Improvements

## Important update

The graph must stay climate-specific. Do not reduce it to only `Paper -> Topic -> Author`.
The correct graph is a Climate Evidence Knowledge Graph with climate nodes such as Country, Policy, ClimateRisk, Sector, Technology, Target, Indicator, Finding, Organization, and Document.

## Priority improvements

1. Replace placeholder dense retrieval with real Qdrant search.
2. Add climate metadata filters to Qdrant: country, region, sector, policy, technology, risk, and topic.
3. Add entity extraction using spaCy, keyword dictionaries, or a small LLM prompt.
4. Make Rana's GraphRAG return graph facts, not only document IDs.
5. Add a page verifier that reopens PDFs and validates cited page ranges.
6. Build 30 gold Q/A pairs that include graph reasoning, not only lookup questions.
7. Add safety tests for fake climate statistics and fake COP commitments.
8. Run ablation: BM25-only, dense-only, hybrid, graph-guided, full GraphRAG + safety.
9. Add caching for embeddings and final answers to improve p95 latency.
10. Keep each member's AI logs separate and tied to their deliverable.

## Strong demo questions

- Which UAE climate policies address renewable energy targets?
- Which climate risks affect agriculture in the Middle East?
- Which documents discuss green hydrogen as a mitigation technology?
- What targets are connected to the COP28 UAE Consensus?
- What climate indicators are used to support sea level rise findings?
- Which AI methods are used in climate forecasting papers?

## Safety examples to test

- Ask for a fake UAE emissions percentage and verify the system refuses.
- Ask the model to ignore citations and verify prompt-injection detection.
- Ask about a non-climate topic and verify unsupported-answer refusal.
- Ask for a policy target and verify citation exists in retrieved chunks.
