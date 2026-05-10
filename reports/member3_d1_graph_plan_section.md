# member3_d1_graph_plan_section.md

## 1. Introduction

My contribution to D1 is the design of the **Climate Evidence Knowledge Graph (Climate-KG)**: the structured knowledge layer that makes our system more than a PDF retrieval tool. While D1 does not require a fully implemented graph, this section establishes the schema, rationale, example queries, and integration plan that will be executed in D2 and D3.

The central idea is that climate reasoning requires more than keyword matching. A question like "which technologies mitigate flooding risks in the Middle East?" requires connecting a technology concept, a risk concept, and a region concept — none of which appear together in any single document chunk. The graph enables this by storing those connections explicitly and using them to guide retrieval before any text is fetched.

---

## 2. Why a Graph? The Case for Climate-KG

Standard RAG systems treat documents as bags of chunks and retrieve based on embedding similarity to a query. This works for factual lookups but fails for climate policy reasoning, which involves:

- **Multi-hop reasoning:** UAE → has policy → UAE Net Zero 2050 → sets target → Triple Renewables → supported by → PDF page 12.
- **Relational filtering:** "Which IPCC documents discuss risks that affect agriculture in MENA?" — this requires joining risk, sector, region, and document provenance simultaneously.
- **Entity disambiguation:** "Carbon capture" appears in hundreds of chunks; the graph node `Technology {name: "Carbon Capture and Storage"}` disambiguates the concept and links it to the right documents.
- **Citation grounding:** Each `Finding` node stores the source document ID and page number, making citation verification deterministic and not dependent on chunk metadata alone.

GraphRAG addresses all four failure modes of plain RAG by using the graph as a structured retrieval index that is layered on top of — not instead of — dense chunk retrieval.

---

## 3. Node Types and Rationale

The Climate-KG contains 15 node types. Each type represents a distinct category of climate knowledge. The table below summarizes each type, its key properties, and why it is included.

| Node Type | Key Properties | Role in Climate Reasoning |
|---|---|---|
| `Document` | `doc_id`, `title`, `year`, `doc_type` | Root evidence node; all claims trace back to a document |
| `Organization` | `org_id`, `name`, `org_type` | Identifies institutional authority (IPCC vs. industry report) |
| `Author` | `name`, `affiliation` | Links research papers to research communities |
| `Venue` | `name`, `venue_type` | Distinguishes peer-reviewed work from grey literature |
| `Country` | `country_id`, `is_annex1` | Enables country-specific policy and risk queries |
| `Region` | `name`, `region_type` | Groups countries for MENA, Global South, or climate-zone queries |
| `ClimateTopic` | `name`, `category` | High-level theme that organizes the domain (mitigation, adaptation, loss and damage) |
| `ClimateRisk` | `name`, `hazard_category`, `confidence_level` | Specific hazard with IPCC confidence metadata |
| `Sector` | `name`, `sector_group` | Economic sector impacted by risks or targeted by policy |
| `Policy` | `name`, `policy_type`, `status`, `year` | Formal commitment with status and scope |
| `Target` | `name`, `value`, `target_year` | Quantified goal linked to a policy |
| `Technology` | `name`, `tech_category` | Solution concept linked to risks and sectors |
| `Indicator` | `name`, `unit` | Measurable metric for findings and targets |
| `Finding` | `text`, `doc_id`, `page`, `confidence` | Anchored evidence claim enabling page-level citation |
| `Method` | `name`, `method_family` | AI/ML method used in climate research papers |

The most critical node for citation integrity is `Finding`. Unlike other nodes, a `Finding` stores both the claim text and the exact page in the source PDF. This means that when GraphRAG retrieves a finding through graph traversal, the system immediately knows which page to fetch from Qdrant for supporting text — no post-hoc search is needed.

---

## 4. Relationship Types and Design Choices

The graph uses 20 directed relationship types. Three design decisions shape this set:

**Decision 1: Separate `DISCUSSES` from `REPORTS_FINDING`.**
A document can discuss sea level rise at a high level (`DISCUSSES → ClimateTopic`) or report a specific quantified claim about it (`REPORTS_FINDING → Finding → HAS_INDICATOR → Indicator`). Keeping these distinct lets the retriever distinguish between background context documents and primary evidence documents.

**Decision 2: Policy connects both upward and downward.**
`Country -[:HAS_POLICY]-> Policy -[:SETS_TARGET]-> Target` and `Policy -[:ADDRESSES]-> ClimateTopic`. This bidirectional traversal means a query about UAE climate commitments can start from the country node, while a query about which policies address biodiversity can start from the topic node. Both reach the same policy cluster through different entry points.

**Decision 3: `Finding -[:SUPPORTED_BY]-> Document` is redundant but intentional.**
Every finding already stores `doc_id` as a property. The `SUPPORTED_BY` relationship duplicates this as a graph edge so that Cypher traversals can follow it without string-matching on properties. This is a standard graph modelling choice for traversal performance.

The full relationship set is defined in `src/graph/graph_schema.md`.

---

## 5. Example Cypher Queries for D2 and D3

These five queries demonstrate how the Climate-KG will support GraphRAG retrieval in later deliverables. They are planned, not yet executed — Neo4j will be populated in D2.

### Query 1 — UAE Renewable Energy Policies
Find all policies adopted by the UAE that address renewable energy, and return the supporting document IDs for each.

```cypher
MATCH (c:Country {country_id: "ARE"})
      -[:HAS_POLICY]->(p:Policy)
      -[:ADDRESSES]->(t:ClimateTopic {category: "mitigation"})
MATCH (p)-[:SETS_TARGET]->(tgt:Target)
OPTIONAL MATCH (p)<-[:SUPPORTED_BY]-(f:Finding)
RETURN p.name AS policy,
       tgt.value AS target,
       tgt.target_year AS deadline,
       collect(DISTINCT f.doc_id) AS evidence_docs
```

**GraphRAG use:** The retriever uses the returned `evidence_docs` list to fetch supporting chunks from Qdrant, instead of running a blind dense search over all documents.

---

### Query 2 — Climate Risks Affecting Agriculture in MENA
Find all climate risks that occur in the MENA region and impact the agriculture sector, with confidence levels.

```cypher
MATCH (r:ClimateRisk)
      -[:OCCURS_IN]->(reg:Region {name: "MENA"})
MATCH (r)-[:IMPACTS]->(s:Sector {sector_group: "agriculture"})
RETURN r.name AS risk,
       r.hazard_category AS category,
       r.confidence_level AS ipcc_confidence
ORDER BY r.confidence_level DESC
```

**GraphRAG use:** The risk names are used to expand the query with climate-specific terminology before dense retrieval, improving recall for domain-specific vocabulary.

---

### Query 3 — Documents Discussing Green Hydrogen
Find all documents that mention green hydrogen, with their publication year and publishing organization.

```cypher
MATCH (d:Document)
      -[:MENTIONS_TECHNOLOGY]->(tech:Technology {name: "Green Hydrogen"})
OPTIONAL MATCH (d)-[:PUBLISHED_BY]->(org:Organization)
RETURN d.title AS title,
       d.year AS year,
       d.doc_type AS type,
       org.name AS publisher
ORDER BY d.year DESC
```

**GraphRAG use:** Returns a prioritized document set for chunk retrieval, ranked by recency.

---

### Query 4 — AI Methods Used in Climate Forecasting Papers
Find all AI methods used in documents that discuss climate forecasting, grouped by method family.

```cypher
MATCH (d:Document)
      -[:DISCUSSES]->(topic:ClimateTopic)
WHERE topic.name CONTAINS "Forecast"
   OR topic.name CONTAINS "Prediction"
MATCH (d)-[:USES_METHOD]->(m:Method)
RETURN m.method_family AS family,
       collect(DISTINCT m.name) AS methods,
       collect(DISTINCT d.doc_id) AS papers
ORDER BY family
```

**GraphRAG use:** Enables the system to answer method-comparison questions by traversing the graph rather than searching for method names in unstructured text.

---

### Query 5 — Multi-Hop: Sea Level Rise → Coastal Sector → MENA Documents
A full multi-hop path from a climate risk to evidence documents, following the graph structure.

```cypher
MATCH path =
  (risk:ClimateRisk {hazard_category: "sea_level"})
    -[:IMPACTS]->(sector:Sector)
    -[:OCCURS_IN*0..1]-(reg:Region {name: "Middle East"})
MATCH (f:Finding)-[:SUPPORTED_BY]->(d:Document)
WHERE f.text CONTAINS sector.name
RETURN risk.name AS risk,
       sector.name AS affected_sector,
       d.title AS source_document,
       f.page AS citation_page,
       f.text AS evidence_claim
LIMIT 10
```

**GraphRAG use:** This is the core GraphRAG pattern: graph traversal identifies the most relevant `Finding` nodes, and the `doc_id` + `page` properties are used as deterministic citation anchors before any vector search is performed.

---

## 6. How the Graph Supports GraphRAG — Integration Plan

The following describes how the Climate-KG integrates with the full pipeline across D2 and D3.

### 6.1 Entity Extraction (D2 — Rana + Salma)

When a user submits a query, a lightweight NLP step extracts climate entity mentions. For example:

> *"Which UAE policies address water scarcity in agriculture?"*

Extracts: `Country = UAE`, `ClimateRisk = Water Scarcity`, `Sector = Agriculture`

These entities become the entry points for Cypher traversal in Neo4j.

### 6.2 Graph-Guided Document Selection (D2 — Rana)

The Cypher traversal returns a ranked list of `Document` IDs and optionally `Finding` IDs with page anchors. These constrain the subsequent vector search in Qdrant: instead of searching all chunks across all documents, dense retrieval runs only within the graph-selected document set.

This is the key efficiency and precision gain: the graph narrows the search space from hundreds of PDFs to the 5–10 most relevant ones before any expensive embedding lookup.

### 6.3 Hybrid Fusion (D2 — Salma)

Graph-guided results are merged with BM25 and dense retrieval results using a fusion strategy. The graph results receive a relevance boost because they are structurally connected to the query entities, not just semantically similar.

### 6.4 Citation-Safe Answer Generation (D3 — Rana + Alia)

The `Finding` node design ensures that every claim in the generated answer can be traced to a specific `doc_id` and `page`. The `citation_builder.py` module will format these as inline citations. The `citation_verifier.py` module (Alia) will then confirm that the cited page actually contains text supporting the claim, using the `page_verifier.py` ingested page map (Reem).

### 6.5 Feedback Adaptation (D3 — Aaya)

When a user rates an answer negatively, the feedback can be attached to specific `Finding` or `Document` nodes in the graph with a `low_quality` flag. Future traversals can deprioritize flagged nodes. This is a graph-native form of the adaptation that Aaya implements in River.

---

## 7. What Makes This Climate-Specific

A general-purpose knowledge graph for document retrieval would contain nodes like `Document`, `Entity`, and `Concept`. The Climate-KG replaces these with nodes that reflect the structure of climate knowledge:

- `ClimateRisk` has a `hazard_category` and `confidence_level` from the IPCC vocabulary.
- `Policy` has a `policy_type` that distinguishes NDCs from strategies from laws.
- `Target` stores a `target_year` and `value`, making numerical climate commitments queryable.
- `Finding` stores an IPCC `confidence` label, which flows into the answer generator's uncertainty framing.
- `Country` stores `is_annex1`, enabling queries about differentiated responsibilities under the UNFCCC framework.

None of these properties are meaningful in a general retrieval system. They are meaningful in climate policy reasoning, which is exactly the domain this project serves.

---

## 8. D2 Implementation Plan

| Task | File | Status |
|---|---|---|
| Implement Neo4j builder with node/relationship creation | `src/graph/neo4j_builder.py` | Planned for D2 |
| Implement Cypher query templates | `src/graph/cypher_queries.py` | Planned for D2 |
| Generate architecture visualization | `docs/climate_evidence_kg_graph.png` | Completed in D1 |
| Write graph_schema.md | `src/graph/graph_schema.md` | Completed in D1 |
| Integrate graph retrieval with GraphRAG executor | `src/rag/graphrag_executor.py` | Planned for D3 |

---

## 9. Summary

The Climate Evidence Knowledge Graph is the structural backbone that distinguishes this project from a simple semantic search tool over PDFs. By modeling climate concepts — risks, policies, targets, technologies, findings, and their relationships — as a typed property graph, the system can answer multi-hop climate questions, constrain retrieval to relevant document sets, and ground every generated claim in a specific document page. The schema designed in D1 is complete and ready for implementation in D2.
