# Climate Evidence GraphRAG Agent

A trusted AI assistant for climate policy, sustainability, climate science, and climate-AI research PDFs.

This updated starter repo is **not only a PDF reader**. PDFs are evidence sources, while the central graph is a **Climate Evidence Knowledge Graph** that connects countries, policies, climate risks, sectors, technologies, targets, indicators, findings, organizations, and source documents.

## Main idea

The user asks a climate question, for example:

- Which UAE climate policies address renewable energy targets?
- Which climate risks affect agriculture in the Middle East?
- Which documents discuss green hydrogen as a mitigation technology?
- What climate impacts are linked to sea level rise?
- Which AI methods are used in climate forecasting papers?

The system:

1. Extracts climate entities from the question.
2. Searches Neo4j for connected climate concepts and evidence documents.
3. Retrieves supporting chunks using BM25 + dense Qdrant search.
4. Blends graph-guided results with global hybrid retrieval.
5. Generates an answer with document/page citations.
6. Verifies citations using source pinning.
7. Learns from feedback using River + ADWIN.

## Architecture graph

See: `docs/architecture_graph.png`

Pipeline summary:

```text
Climate PDFs
  -> PDF parser + page map
  -> chunking + climate metadata
  -> embeddings
  -> MongoDB + Qdrant + Neo4j Climate Evidence KG
  -> BM25 + dense retrieval + climate Cypher expansion
  -> hybrid fusion + reranking
  -> citation-safe answer generation
  -> user feedback
  -> River + ADWIN adaptation
```

## Climate Evidence Knowledge Graph

See: `docs/climate_evidence_kg_graph.png`

### Nodes

```text
Document, Organization, Country, Region, ClimateTopic, ClimateRisk,
ClimateImpact, Sector, Policy, Target, Technology, Indicator,
Finding, Method, Author, Venue
```

### Relationships

```cypher
(:Document)-[:PUBLISHED_BY]->(:Organization)
(:Document)-[:DISCUSSES]->(:ClimateTopic)
(:Document)-[:REPORTS_FINDING]->(:Finding)
(:Finding)-[:SUPPORTED_BY]->(:Document)
(:Finding)-[:HAS_INDICATOR]->(:Indicator)
(:Finding)-[:AFFECTS]->(:Sector)
(:ClimateRisk)-[:IMPACTS]->(:Sector)
(:ClimateRisk)-[:OCCURS_IN]->(:Region)
(:Country)-[:LOCATED_IN]->(:Region)
(:Country)-[:HAS_POLICY]->(:Policy)
(:Policy)-[:SETS_TARGET]->(:Target)
(:Policy)-[:ADDRESSES]->(:ClimateTopic)
(:Technology)-[:MITIGATES]->(:ClimateRisk)
(:Technology)-[:USED_IN]->(:Sector)
(:Document)-[:MENTIONS_COUNTRY]->(:Country)
(:Document)-[:MENTIONS_TECHNOLOGY]->(:Technology)
(:Document)-[:USES_METHOD]->(:Method)
(:Author)-[:WROTE]->(:Document)
(:Document)-[:PUBLISHED_IN]->(:Venue)
```
