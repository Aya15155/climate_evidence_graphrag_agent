# Climate Evidence Knowledge Graph — Schema v2.0

## Overview

This schema defines the **Climate Evidence Knowledge Graph (Climate-KG)** for the CSAI415
Climate Evidence GraphRAG Agent. It is a Neo4j property graph that treats climate knowledge
as an interconnected network of evidence, policies, risks, technologies, sectors, and findings.

This schema is the intelligence layer above the PDF corpus. PDFs are evidence sources.
The graph is what makes multi-hop climate reasoning possible.

### What changed from v1.0

| Area | v1.0 gap | v2.0 fix |
|---|---|---|
| Finding connectivity | Finding only linked to Document and Indicator | Finding now has direct edges to ClimateRisk, Sector, Country, Technology |
| Scenario node | Missing entirely | Added `Scenario` node (SSP pathways, warming levels) |
| Risk cascades | No risk-to-risk edges | Added `LEADS_TO` on ClimateRisk for compound risk chains |
| Policy evolution | No temporal policy links | Added `SUPERSEDES` on Policy |
| Document provenance | No citation edges | Added `CITES` on Document → Document |
| Relationship quality | No confidence on edges | Added `confidence`, `source` properties to causal relationships |
| Entity deduplication | Name-string MERGE only | All nodes use slug IDs; canonical name normalisation required before MERGE |
| Author/Method realism | Both populated from all doc types | Scoped: Author only for research papers, Method only for AI/ML papers |

---

## Node Types

Properties marked `*` are required. All `*_id` fields are stable slugs,
not display names, and must be generated via `normalize_entity_name()` before MERGE.

---

### `Document`

Represents a source PDF ingested into the system.

| Property | Type | Description |
|---|---|---|
| `doc_id` * | String | Stable slug (e.g., `ipcc_ar6_wg1`) |
| `title` * | String | Full document title |
| `year` | Integer | Publication year |
| `doc_type` | String | `policy` \| `ipcc_report` \| `cop_document` \| `research_paper` \| `ndc` \| `strategy` |
| `language` | String | ISO language code (default `en`) |
| `url` | String | Source URL if available |
| `page_count` | Integer | Total pages in the PDF |
| `ingested_at` | String | ISO timestamp of ingestion |

**Example:**
```cypher
MERGE (:Document {
  doc_id: "uae_netzero_2050",
  title: "UAE Net Zero by 2050 Strategic Initiative",
  year: 2021,
  doc_type: "strategy",
  language: "en",
  page_count: 48,
  ingested_at: "2024-01-15T10:00:00Z"
})
```

---

### `Organization`

An institution that publishes or endorses climate documents.

| Property | Type | Description |
|---|---|---|
| `org_id` * | String | Stable slug (e.g., `ipcc`, `unfccc`, `moccae`) |
| `name` * | String | Full organization name |
| `org_type` | String | `intergovernmental` \| `government` \| `ngo` \| `research` \| `industry` |
| `country_code` | String | ISO 3166-1 alpha-2 if national body |

---

### `Author`

A named author of a **research paper only**. Do not create Author nodes for policy documents.

| Property | Type | Description |
|---|---|---|
| `author_id` * | String | Stable slug from name |
| `name` * | String | Full name |
| `affiliation` | String | Institutional affiliation |
| `orcid` | String | ORCID identifier if available |

---

### `Venue`

A journal, conference, or series where a document was published.

| Property | Type | Description |
|---|---|---|
| `venue_id` * | String | Stable slug |
| `name` * | String | Full venue name |
| `venue_type` | String | `journal` \| `conference` \| `report_series` \| `government_publication` |

---

### `Country`

A nation mentioned or targeted in climate documents.

| Property | Type | Description |
|---|---|---|
| `country_id` * | String | **ISO 3166-1 alpha-3** (e.g., `ARE`, `DEU`) — always use ISO code, never country name, as MERGE key |
| `name` * | String | Canonical country name |
| `income_group` | String | World Bank income group |
| `is_annex1` | Boolean | UNFCCC Annex I party |

**Example:**
```cypher
MERGE (:Country {
  country_id: "ARE",
  name: "United Arab Emirates",
  income_group: "high",
  is_annex1: false
})
```

---

### `Region`

A geographic or geopolitical region broader than a country.

| Property | Type | Description |
|---|---|---|
| `region_id` * | String | Stable slug (e.g., `mena`, `gulf_cooperation_council`) |
| `name` * | String | Region name |
| `region_type` | String | `geographic` \| `climate_zone` \| `political_bloc` |

**Examples:** `Middle East`, `MENA`, `Global South`, `Small Island States`, `Gulf Cooperation Council`

---

### `ClimateTopic`

A high-level climate science or policy theme. Used for broad document classification.

| Property | Type | Description |
|---|---|---|
| `topic_id` * | String | Stable slug |
| `name` * | String | Topic name |
| `category` | String | `mitigation` \| `adaptation` \| `loss_and_damage` \| `finance` \| `science` \| `governance` |
| `ipcc_chapter` | String | IPCC AR6 chapter reference if applicable |

---

### `ClimateRisk`

A specific climate hazard or risk that threatens systems or sectors.

| Property | Type | Description |
|---|---|---|
| `risk_id` * | String | Stable slug (e.g., `heatwaves`, `coastal_flooding`) |
| `name` * | String | Canonical risk name |
| `risk_type` | String | `physical` \| `transition` \| `liability` |
| `hazard_category` | String | `extreme_heat` \| `flooding` \| `drought` \| `sea_level` \| `storm` \| `wildfire` \| `water_scarcity` |
| `confidence_level` | String | IPCC confidence label (`high` \| `very_high` \| `medium`) |

**Examples:** `Heatwaves`, `Coastal Flooding`, `Water Scarcity`, `Desertification`, `Marine Heatwaves`

---

### `Sector`

An economic or social sector affected by climate risks or targeted by policies.

| Property | Type | Description |
|---|---|---|
| `sector_id` * | String | Stable slug (e.g., `renewable_energy`, `agriculture`) |
| `name` * | String | Sector name |
| `sector_group` | String | `energy` \| `land` \| `transport` \| `buildings` \| `industry` \| `water` \| `health` \| `agriculture` \| `ecosystem` |

---

### `Policy`

A formal climate policy, agreement, NDC, or law.

| Property | Type | Description |
|---|---|---|
| `policy_id` * | String | Stable slug |
| `name` * | String | Policy name |
| `policy_type` | String | `ndc` \| `law` \| `strategy` \| `international_agreement` \| `regulation` \| `action_plan` |
| `status` | String | `adopted` \| `proposed` \| `under_review` \| `expired` |
| `year` | Integer | Year enacted or submitted |
| `scope` | String | `national` \| `regional` \| `global` \| `sectoral` |

**Example:**
```cypher
MERGE (:Policy {
  policy_id: "uae_netzero_2050_policy",
  name: "UAE Net Zero by 2050",
  policy_type: "strategy",
  status: "adopted",
  year: 2021,
  scope: "national"
})
```

---

### `Target`

A quantified climate commitment or goal set by a policy.

| Property | Type | Description |
|---|---|---|
| `target_id` * | String | Stable slug |
| `name` * | String | Short target label |
| `description` | String | Full target description |
| `target_year` | Integer | Deadline year (e.g., `2030`, `2050`) |
| `metric` | String | What is measured (e.g., `GHG emissions`, `renewable share`) |
| `value` | String | Quantified goal (e.g., `44% reduction`, `triple renewables`) |
| `baseline_year` | Integer | Reference year |

**Example:**
```cypher
MERGE (:Target {
  target_id: "cop28_triple_renewables_2030",
  name: "Triple Global Renewables by 2030",
  target_year: 2030,
  metric: "renewable energy capacity",
  value: "3x 2022 baseline",
  baseline_year: 2022
})
```

---

### `Technology`

A climate technology or solution mentioned in the literature.

| Property | Type | Description |
|---|---|---|
| `tech_id` * | String | Stable slug (e.g., `green_hydrogen`, `solar_pv`) |
| `name` * | String | Canonical technology name |
| `tech_category` | String | `renewable_energy` \| `carbon_removal` \| `efficiency` \| `adaptation` \| `storage` \| `hydrogen` |
| `trl` | Integer | Technology Readiness Level (1–9) if known |

**Examples:** `Green Hydrogen`, `Solar PV`, `Carbon Capture and Storage`, `Desalination`, `Direct Air Capture`

---

### `Indicator`

A measurable climate metric used to track findings or targets.

| Property | Type | Description |
|---|---|---|
| `indicator_id` * | String | Stable slug |
| `name` * | String | Indicator name |
| `unit` | String | Unit of measurement |
| `indicator_type` | String | `emissions` \| `temperature` \| `sea_level` \| `economic` \| `biodiversity` \| `energy` |

**Examples:** `CO2 concentration (ppm)`, `Global mean temperature anomaly (°C)`, `Renewable share (%)`

---

### `Finding`  *(upgraded in v2.0)*

A specific evidence claim extracted from a document, anchored to a page.
Findings are the bridge between graph structure and PDF evidence text.
Every Finding must connect to at least one entity node (risk, sector, country, or technology).

| Property | Type | Description |
|---|---|---|
| `finding_id` * | String | `{doc_id}_p{page}_{6-char hash of text}` |
| `text` * | String | The evidence claim statement |
| `doc_id` * | String | Source document ID (must match a Document node) |
| `page` * | Integer | Page number in source PDF (required for Qdrant chunk lookup) |
| `confidence` | String | IPCC confidence label or extraction confidence |
| `extraction_method` | String | `manual` \| `llm_extracted` \| `rule_based` |
| `qdrant_chunk_id` | String | Corresponding Qdrant chunk ID for hybrid retrieval |

**Example:**
```cypher
MERGE (:Finding {
  finding_id: "ipcc_ar6_wg1_p5_a3f9b2",
  text: "Global mean sea level has risen faster since 1900 than over any preceding century in at least the last 3000 years.",
  doc_id: "ipcc_ar6_wg1",
  page: 5,
  confidence: "high",
  extraction_method: "manual",
  qdrant_chunk_id: "ipcc_ar6_wg1_chunk_042"
})
```

---

### `Scenario`  *(new in v2.0)*

An IPCC climate scenario or warming pathway. Contextualises quantitative findings and targets.

| Property | Type | Description |
|---|---|---|
| `scenario_id` * | String | Stable slug (e.g., `ssp2_4_5`, `ssp5_8_5`) |
| `name` * | String | Scenario label (e.g., `SSP2-4.5`) |
| `warming_level` | Float | Projected warming in °C above pre-industrial by 2100 |
| `time_horizon` | Integer | Projection end year |
| `description` | String | Narrative description of the scenario pathway |

**Examples:** `SSP1-1.9` (1.5°C), `SSP2-4.5` (2.7°C), `SSP5-8.5` (4.4°C)

---

### `Method`

An AI or computational method used in a **research paper only**.

| Property | Type | Description |
|---|---|---|
| `method_id` * | String | Stable slug |
| `name` * | String | Method name |
| `method_family` | String | `deep_learning` \| `statistical` \| `physical_model` \| `hybrid` \| `reinforcement_learning` |
| `task` | String | Climate task the method is applied to |

---

## Relationship Types

All relationships are directed. Relationships with causal or inferential meaning carry
`confidence` and `source` properties to allow evidence-quality filtering.

### Document-level relationships (safe to automate from metadata)

| Relationship | From → To | Properties | Notes |
|---|---|---|---|
| `PUBLISHED_BY` | `Document → Organization` | — | Direct metadata field; always safe |
| `WROTE` | `Author → Document` | — | Research papers only |
| `PUBLISHED_IN` | `Document → Venue` | — | Direct metadata field |
| `DISCUSSES` | `Document → ClimateTopic` | — | From editorial topic tags |
| `MENTIONS_COUNTRY` | `Document → Country` | — | Asserts mention only, not causality |
| `MENTIONS_TECHNOLOGY` | `Document → Technology` | — | Asserts mention only |
| `USES_METHOD` | `Document → Method` | — | Research papers only |
| `REPORTS_FINDING` | `Document → Finding` | — | Always safe; Finding must have non-null page |
| `CITES` | `Document → Document` | `page` | *(new v2.0)* Inter-document citation |

### Finding-level relationships (require PDF extraction, not metadata inference)

| Relationship | From → To | Properties | Notes |
|---|---|---|---|
| `SUPPORTED_BY` | `Finding → Document` | `page` | Bidirectional provenance with page anchor |
| `HAS_INDICATOR` | `Finding → Indicator` | — | Quantified evidence |
| `EVIDENCES_RISK` | `Finding → ClimateRisk` | `confidence`, `source` | *(new v2.0)* Direct evidence edge |
| `EVIDENCES_SECTOR` | `Finding → Sector` | `confidence`, `source` | *(new v2.0)* Direct evidence edge |
| `EVIDENCES_COUNTRY` | `Finding → Country` | `confidence`, `source` | *(new v2.0)* Direct evidence edge |
| `EVIDENCES_TECHNOLOGY` | `Finding → Technology` | `confidence`, `source` | *(new v2.0)* Direct evidence edge |
| `UNDER_SCENARIO` | `Finding → Scenario` | — | *(new v2.0)* Scenario context for quantitative findings |

### Geographic relationships (safe to automate)

| Relationship | From → To | Properties | Notes |
|---|---|---|---|
| `LOCATED_IN` | `Country → Region` | — | Geographic fact; stable |

### Policy relationships (gate on doc_type before automating)

| Relationship | From → To | Properties | Notes |
|---|---|---|---|
| `HAS_POLICY` | `Country → Policy` | `source` | Only write if doc_type is ndc/strategy/law |
| `POLICY_SCOPE` | `Policy → Region` | — | Regional policies only |
| `SETS_TARGET` | `Policy → Target` | `confidence`, `source` | Require both in same document |
| `ADDRESSES` | `Policy → ClimateTopic` | — | Accept from policy/ndc/strategy doc_type |
| `SUPERSEDES` | `Policy → Policy` | `year` | *(new v2.0)* NDC evolution |
| `ASSUMES_SCENARIO` | `Target → Scenario` | — | *(new v2.0)* Target under scenario context |

### Causal relationships (require Finding-level evidence; never infer from metadata co-occurrence)

| Relationship | From → To | Properties | Notes |
|---|---|---|---|
| `HAS_RISK` | `ClimateTopic → ClimateRisk` | — | Topic involves this specific risk |
| `IMPACTS` | `ClimateRisk → Sector` | `confidence`, `source` | Only from Finding evidence |
| `OCCURS_IN` | `ClimateRisk → Region` | `confidence`, `source` | Only from Finding evidence |
| `LEADS_TO` | `ClimateRisk → ClimateRisk` | `confidence`, `source` | *(new v2.0)* Cascade/compound risk chain |
| `MITIGATES` | `Technology → ClimateRisk` | `confidence`, `source` | Only from Finding evidence |
| `USED_IN` | `Technology → Sector` | — | Technology deployment context |

---

## Relationship Property Standards

Causal relationships (`IMPACTS`, `MITIGATES`, `OCCURS_IN`, `LEADS_TO`, `EVIDENCES_*`) must include:

```
confidence: "high" | "medium" | "low"   — IPCC label or extraction confidence
source: "manual" | "llm_extracted" | "rule_based" | "metadata"
```

This allows GraphRAG queries to filter by evidence quality:
```cypher
MATCH (t:Technology)-[r:MITIGATES]->(risk:ClimateRisk)
WHERE r.confidence IN ["high", "medium"]
AND r.source <> "metadata"
RETURN t.name, risk.name, r.confidence
```

---

## Multi-Hop Path Examples

### Path 1 — UAE Renewable Policy Chain *(Country → Policy → Target)*
```
(UAE:Country)
  -[:HAS_POLICY]->
(UAE Net Zero 2050:Policy)
  -[:SETS_TARGET]->
(Triple Renewables by 2030:Target)
  <-[:SUPPORTED_BY]-
(Finding {page: 12})
  <-[:REPORTS_FINDING]-
(uae_netzero_2050:Document)
```
**Answers:** "What renewable targets has the UAE committed to, and on which page?"

---

### Path 2 — Sea Level Rise Impact Chain *(ClimateRisk → Sector → Region)*
```
(Sea Level Rise:ClimateRisk)
  -[:IMPACTS {confidence: "high"}]->
(Coastal Infrastructure:Sector)
  <-[:EVIDENCES_SECTOR]-
(Finding {page: 1147})
  -[:EVIDENCES_RISK]->
(Sea Level Rise:ClimateRisk)
  -[:OCCURS_IN]->
(Middle East:Region)
```
**Answers:** "Which sectors in the Middle East face high-confidence sea level rise risks?"

---

### Path 3 — Green Hydrogen Mitigation Chain *(Technology → MITIGATES → ClimateRisk)*
```
(Green Hydrogen:Technology)
  -[:MITIGATES {confidence: "medium"}]->
(Carbon Emissions:ClimateRisk)
  <-[:EVIDENCES_RISK]-
(Finding)
  <-[:REPORTS_FINDING]-
(cop28_synthesis:Document)
  -[:PUBLISHED_BY]->
(UNFCCC:Organization)
```
**Answers:** "Which UNFCCC documents provide evidence for green hydrogen as a mitigation option?"

---

### Path 4 — Compound Risk Cascade *(new v2.0)*
```
(Heatwaves:ClimateRisk)
  -[:LEADS_TO]->
(Water Scarcity:ClimateRisk)
  -[:LEADS_TO]->
(Desertification:ClimateRisk)
  -[:OCCURS_IN]->
(MENA:Region)
  <-[:LOCATED_IN]-
(UAE:Country)
  -[:HAS_POLICY]->
(UAE Food Security Strategy:Policy)
```
**Answers:** "What cascade risks and policies apply to the UAE under compound climate stress?"

---

### Path 5 — Evidence Grounding Chain *(Finding → Document)*
```
(Agriculture:Sector)
  <-[:EVIDENCES_SECTOR]-
(Finding {text: "...", page: 34, confidence: "high"})
  <-[:REPORTS_FINDING]-
(ipcc_ar6_wg2:Document {doc_type: "ipcc_report"})
  -[:PUBLISHED_BY]->
(IPCC:Organization)
```
**Answers:** "What IPCC-sourced, page-anchored evidence exists for climate impacts on agriculture?"

---

## Constraints and Indexes

Run once when initialising the Neo4j database (via `ClimateGraphBuilder.run_constraints()`).

```cypher
-- Uniqueness constraints
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS
  FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;

CREATE CONSTRAINT org_id_unique IF NOT EXISTS
  FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;

CREATE CONSTRAINT country_id_unique IF NOT EXISTS
  FOR (c:Country) REQUIRE c.country_id IS UNIQUE;

CREATE CONSTRAINT risk_id_unique IF NOT EXISTS
  FOR (r:ClimateRisk) REQUIRE r.risk_id IS UNIQUE;

CREATE CONSTRAINT policy_id_unique IF NOT EXISTS
  FOR (p:Policy) REQUIRE p.policy_id IS UNIQUE;

CREATE CONSTRAINT finding_id_unique IF NOT EXISTS
  FOR (f:Finding) REQUIRE f.finding_id IS UNIQUE;

CREATE CONSTRAINT tech_id_unique IF NOT EXISTS
  FOR (t:Technology) REQUIRE t.tech_id IS UNIQUE;

CREATE CONSTRAINT sector_id_unique IF NOT EXISTS
  FOR (s:Sector) REQUIRE s.sector_id IS UNIQUE;

CREATE CONSTRAINT region_id_unique IF NOT EXISTS
  FOR (r:Region) REQUIRE r.region_id IS UNIQUE;

CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS
  FOR (s:Scenario) REQUIRE s.scenario_id IS UNIQUE;

CREATE CONSTRAINT target_id_unique IF NOT EXISTS
  FOR (t:Target) REQUIRE t.target_id IS UNIQUE;

-- Full-text index for semantic search on Finding text
CREATE FULLTEXT INDEX finding_text_index IF NOT EXISTS
  FOR (f:Finding) ON EACH [f.text];

-- Index on Document year for temporal filtering
CREATE INDEX doc_year_index IF NOT EXISTS
  FOR (d:Document) ON (d.year);

-- Index on ClimateRisk type for hazard filtering
CREATE INDEX risk_type_index IF NOT EXISTS
  FOR (r:ClimateRisk) ON (r.risk_type);

-- Index on Policy year for temporal policy queries
CREATE INDEX policy_year_index IF NOT EXISTS
  FOR (p:Policy) ON (p.year);

-- Index on Finding page for Qdrant chunk lookups
CREATE INDEX finding_page_index IF NOT EXISTS
  FOR (f:Finding) ON (f.doc_id, f.page);
```

---

## Entity Normalisation Rules

Before any MERGE operation, apply these transformations in order:
1. Strip leading/trailing whitespace
2. Collapse internal whitespace to single space
3. Apply alias lookup table (YAML file at `src/graph/aliases.yaml`)
4. For `*_id` fields: lowercase, replace spaces with underscores, remove special characters

**Alias examples** (see `aliases.yaml` for full list):
```
"renewables"         → "Renewable Energy"
"solar"              → "Solar PV"
"uae"                → "United Arab Emirates"
"gcc"                → "Gulf Cooperation Council"
"net zero"           → "Net Zero by 2050"
"slr"                → "Sea Level Rise"
"ccs"                → "Carbon Capture and Storage"
"dac"                → "Direct Air Capture"
"mena"               → "Middle East and North Africa"
```

---

## Design Rationale

Three core design decisions differentiate this schema from a plain document graph:

**1. Findings are evidence anchors, not text blobs.**
Every `Finding` node stores `doc_id` + `page` + `qdrant_chunk_id`. GraphRAG can traverse from
a graph path (e.g., risk → sector → finding) directly to the PDF page and the Qdrant chunk,
making citation verification deterministic rather than probabilistic.

**2. Causal relationships are evidence-gated.**
`IMPACTS`, `MITIGATES`, `OCCURS_IN`, and `LEADS_TO` are never written from metadata
co-occurrence. They require a `Finding` node as evidence anchor. This prevents the graph
from asserting that "heatwaves impact agriculture" simply because a document mentions
both — the claim must be grounded in an extracted evidence statement.

**3. Policies connect upward and downward.**
A `Policy` node connects upward to `Country` and `Region`, and downward to `Target` and
`ClimateTopic`. This enables bidirectional traversal: "what has the UAE committed to?"
(downward) and "which countries have adopted net-zero policies?" (upward from `Target`).
The `SUPERSEDES` edge additionally allows temporal policy evolution queries across NDC cycles.