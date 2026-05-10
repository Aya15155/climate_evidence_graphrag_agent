# Climate Evidence Knowledge Graph — Schema

## Overview

This schema defines the structure of the **Climate Evidence Knowledge Graph (Climate-KG)**, a Neo4j property graph that makes the system climate-specific. Rather than treating PDFs as flat text, the graph models climate knowledge as an interconnected network of concepts, policies, risks, technologies, findings, and evidence documents. This structure enables GraphRAG: multi-hop reasoning that follows concept chains through the graph before fetching supporting text chunks.

PDFs are evidence sources. The graph is the intelligence layer.

---

## Node Types

Each node type captures a distinct climate concept. Properties marked `*` are required for every node of that type.

---

### `Document`

Represents a source PDF ingested into the system.

| Property | Type | Description |
|---|---|---|
| `doc_id` * | String | Unique identifier (e.g., `ipcc_ar6_wg1`) |
| `title` * | String | Full document title |
| `year` | Integer | Publication year |
| `doc_type` | String | One of: `policy`, `ipcc_report`, `cop_document`, `research_paper`, `ndc`, `strategy` |
| `language` | String | ISO language code (default `en`) |
| `url` | String | Source URL if available |
| `page_count` | Integer | Total pages in the PDF |
| `ingested_at` | Datetime | Timestamp of ingestion |

**Example:**
```cypher
CREATE (:Document {
  doc_id: "uae_netzero_2050",
  title: "UAE Net Zero by 2050 Strategic Initiative",
  year: 2021,
  doc_type: "strategy",
  language: "en",
  page_count: 48
})
```

---

### `Organization`

An institution that publishes or endorses climate documents.

| Property | Type | Description |
|---|---|---|
| `org_id` * | String | Unique identifier (e.g., `ipcc`, `unfccc`) |
| `name` * | String | Full organization name |
| `org_type` | String | One of: `intergovernmental`, `government`, `ngo`, `research`, `industry` |
| `country_code` | String | ISO country code if national body |

**Example:**
```cypher
CREATE (:Organization {
  org_id: "moccae",
  name: "Ministry of Climate Change and Environment",
  org_type: "government",
  country_code: "AE"
})
```

---

### `Author`

A named author of a research paper or report.

| Property | Type | Description |
|---|---|---|
| `author_id` * | String | Unique identifier |
| `name` * | String | Full name |
| `affiliation` | String | Institutional affiliation |
| `orcid` | String | ORCID identifier if available |

---

### `Venue`

A journal, conference, or series where a document was published.

| Property | Type | Description |
|---|---|---|
| `venue_id` * | String | Unique identifier |
| `name` * | String | Full venue name |
| `venue_type` | String | One of: `journal`, `conference`, `report_series`, `government_publication` |

---

### `Country`

A nation mentioned or targeted in climate documents.

| Property | Type | Description |
|---|---|---|
| `country_id` * | String | ISO 3166-1 alpha-3 code (e.g., `ARE`, `DEU`) |
| `name` * | String | Country name |
| `income_group` | String | World Bank income group |
| `is_annex1` | Boolean | UNFCCC Annex I party |

**Example:**
```cypher
CREATE (:Country {
  country_id: "ARE",
  name: "United Arab Emirates",
  income_group: "high",
  is_annex1: false
})
```

---

### `Region`

A geographic or geopolitical region (broader than a country).

| Property | Type | Description |
|---|---|---|
| `region_id` * | String | Unique identifier |
| `name` * | String | Region name |
| `region_type` | String | One of: `geographic`, `climate_zone`, `political_bloc` |

**Examples:** `Middle East`, `Global South`, `MENA`, `Small Island States`, `Sub-Saharan Africa`

---

### `ClimateTopic`

A high-level climate science or policy theme.

| Property | Type | Description |
|---|---|---|
| `topic_id` * | String | Unique identifier |
| `name` * | String | Topic name |
| `category` | String | One of: `mitigation`, `adaptation`, `loss_and_damage`, `finance`, `science`, `governance` |
| `ipcc_chapter` | String | Relevant IPCC AR6 chapter reference if applicable |

**Examples:** `Sea Level Rise`, `Carbon Pricing`, `Climate Finance`, `Renewable Energy Transition`, `Biodiversity Loss`

---

### `ClimateRisk`

A specific climate hazard or risk that threatens systems or sectors.

| Property | Type | Description |
|---|---|---|
| `risk_id` * | String | Unique identifier |
| `name` * | String | Risk name |
| `risk_type` | String | One of: `physical`, `transition`, `liability` |
| `hazard_category` | String | One of: `extreme_heat`, `flooding`, `drought`, `sea_level`, `storm`, `wildfire`, `water_scarcity` |
| `confidence_level` | String | IPCC confidence label (e.g., `high`, `very high`) |

**Examples:** `Heatwaves`, `Coastal Flooding`, `Water Scarcity`, `Desertification`, `Marine Heatwaves`

---

### `Sector`

An economic or social sector affected by climate risks or targeted by policies.

| Property | Type | Description |
|---|---|---|
| `sector_id` * | String | Unique identifier |
| `name` * | String | Sector name |
| `sector_group` | String | One of: `energy`, `land`, `transport`, `buildings`, `industry`, `water`, `health`, `agriculture`, `ecosystem` |

**Examples:** `Renewable Energy`, `Agriculture`, `Coastal Infrastructure`, `Public Health`, `Fisheries`

---

### `Policy`

A formal climate policy, agreement, NDC, or law.

| Property | Type | Description |
|---|---|---|
| `policy_id` * | String | Unique identifier |
| `name` * | String | Policy name |
| `policy_type` | String | One of: `ndc`, `law`, `strategy`, `international_agreement`, `regulation`, `action_plan` |
| `status` | String | One of: `adopted`, `proposed`, `under_review`, `expired` |
| `year` | Integer | Year enacted or submitted |
| `scope` | String | One of: `national`, `regional`, `global`, `sectoral` |

**Example:**
```cypher
CREATE (:Policy {
  policy_id: "uae_netzero_policy",
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
| `target_id` * | String | Unique identifier |
| `name` * | String | Short target label |
| `description` | String | Full target description |
| `target_year` | Integer | Deadline year (e.g., `2030`, `2050`) |
| `metric` | String | What is being measured (e.g., `GHG emissions`, `renewable share`) |
| `value` | String | Quantified goal (e.g., `44% reduction`, `triple renewables`) |
| `baseline_year` | Integer | Reference year |

**Example:**
```cypher
CREATE (:Target {
  target_id: "cop28_triple_renewables",
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
| `tech_id` * | String | Unique identifier |
| `name` * | String | Technology name |
| `tech_category` | String | One of: `renewable_energy`, `carbon_removal`, `efficiency`, `adaptation`, `storage`, `hydrogen` |
| `trl` | Integer | Technology Readiness Level (1–9) if known |

**Examples:** `Green Hydrogen`, `Solar PV`, `Carbon Capture and Storage`, `Desalination`, `Direct Air Capture`

---

### `Indicator`

A measurable climate metric used to track findings or targets.

| Property | Type | Description |
|---|---|---|
| `indicator_id` * | String | Unique identifier |
| `name` * | String | Indicator name |
| `unit` | String | Unit of measurement |
| `indicator_type` | String | One of: `emissions`, `temperature`, `sea_level`, `economic`, `biodiversity`, `energy` |

**Examples:** `CO2 concentration (ppm)`, `Global mean temperature anomaly (°C)`, `Sea level rise (mm/yr)`, `Renewable share (%)`, `Adaptation finance ($B)`

---

### `Finding`

A specific evidence claim extracted from a document, anchored to a page.

| Property | Type | Description |
|---|---|---|
| `finding_id` * | String | Unique identifier |
| `text` * | String | The claim or evidence statement |
| `doc_id` * | String | Source document ID |
| `page` | Integer | Page number in source PDF |
| `confidence` | String | IPCC or author confidence label |
| `extraction_method` | String | One of: `manual`, `llm_extracted`, `rule_based` |

**Example:**
```cypher
CREATE (:Finding {
  finding_id: "f_ar6_slr_001",
  text: "Global mean sea level has risen faster since 1900 than over any preceding century in at least the last 3000 years.",
  doc_id: "ipcc_ar6_wg1",
  page: 5,
  confidence: "high",
  extraction_method: "manual"
})
```

---

### `Method`

An AI or computational method used in a climate research paper.

| Property | Type | Description |
|---|---|---|
| `method_id` * | String | Unique identifier |
| `name` * | String | Method name |
| `method_family` | String | One of: `deep_learning`, `statistical`, `physical_model`, `hybrid`, `reinforcement_learning` |
| `task` | String | Climate task the method is applied to |

**Examples:** `Transformer`, `LSTM`, `Statistical Downscaling`, `Random Forest`, `Physics-Informed Neural Network`

---

## Relationship Types

Each relationship captures a climate-meaningful connection between node types. All relationships are directed.

| Relationship | From → To | Description |
|---|---|---|
| `PUBLISHED_BY` | `Document → Organization` | The document was published or endorsed by this organization |
| `WROTE` | `Author → Document` | The author wrote or co-authored the document |
| `PUBLISHED_IN` | `Document → Venue` | The document appeared in this journal or conference |
| `DISCUSSES` | `Document → ClimateTopic` | The document covers this climate topic |
| `MENTIONS_COUNTRY` | `Document → Country` | The document explicitly mentions this country |
| `MENTIONS_TECHNOLOGY` | `Document → Technology` | The document discusses this technology |
| `USES_METHOD` | `Document → Method` | A research paper applies this AI/ML method |
| `REPORTS_FINDING` | `Document → Finding` | The document contains this finding with page anchor |
| `SUPPORTED_BY` | `Finding → Document` | The finding is supported by this document (with page) |
| `HAS_INDICATOR` | `Finding → Indicator` | The finding is quantified by this indicator |
| `LOCATED_IN` | `Country → Region` | The country belongs to this region |
| `HAS_POLICY` | `Country → Policy` | The country has adopted this policy |
| `POLICY_SCOPE` | `Policy → Region` | The policy applies to this region |
| `SETS_TARGET` | `Policy → Target` | The policy commits to this quantified target |
| `ADDRESSES` | `Policy → ClimateTopic` | The policy addresses this climate topic |
| `HAS_RISK` | `ClimateTopic → ClimateRisk` | This topic involves this specific risk |
| `IMPACTS` | `ClimateRisk → Sector` | This risk negatively impacts this sector |
| `OCCURS_IN` | `ClimateRisk → Region` | This risk is projected or observed in this region |
| `MITIGATES` | `Technology → ClimateRisk` | This technology reduces or counters this risk |
| `USED_IN` | `Technology → Sector` | This technology is deployed in this sector |

---

## Multi-Hop Path Examples

These paths illustrate how GraphRAG traverses multiple hops to answer climate questions.

### Path 1 — UAE Renewable Policy Chain
```
(UAE:Country)
  -[:HAS_POLICY]->
(UAE Net Zero 2050:Policy)
  -[:SETS_TARGET]->
(Triple Renewables:Target)
  -[:SUPPORTED_BY]->
(uae_netzero_2050:Document {page: 12})
```
**Answers:** "What renewable targets has the UAE committed to, and where is this documented?"

---

### Path 2 — Sea Level Rise Impact Chain
```
(Sea Level Rise:ClimateRisk)
  -[:IMPACTS]->
(Coastal Infrastructure:Sector)
  -[:OCCURS_IN]->
(Middle East:Region)
  -[:SUPPORTED_BY]->
(ipcc_ar6_wg2:Document {page: 1147})
```
**Answers:** "Which sectors in the Middle East are most affected by sea level rise?"

---

### Path 3 — Green Hydrogen Mitigation Chain
```
(Green Hydrogen:Technology)
  -[:MITIGATES]->
(Carbon Emissions:ClimateRisk)
  -[:MENTIONED_IN]->
(cop28_synthesis:Document)
  -[:PUBLISHED_BY]->
(UNFCCC:Organization)
```
**Answers:** "Which UNFCCC documents discuss green hydrogen as a mitigation option?"

---

### Path 4 — AI Method in Forecasting
```
(Transformer:Method)
  <-[:USES_METHOD]-
(climate_dl_paper_01:Document)
  -[:DISCUSSES]->
(Climate Forecasting:ClimateTopic)
```
**Answers:** "Which papers use Transformer models for climate forecasting?"

---

### Path 5 — Agriculture Risk in MENA
```
(Water Scarcity:ClimateRisk)
  -[:OCCURS_IN]->
(MENA:Region)
  -[:IMPACTS]->
(Agriculture:Sector)
  -[:HAS_POLICY]->
(UAE Food Security Strategy:Policy)
```
**Answers:** "What policies address water scarcity risks to agriculture in MENA?"

---

## Constraints and Indexes

The following Cypher statements should be run once when initializing the Neo4j database.

```cypher
-- Uniqueness constraints (one per node type)
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

-- Full-text index for semantic search on Finding text
CREATE FULLTEXT INDEX finding_text_index IF NOT EXISTS
  FOR (f:Finding) ON EACH [f.text];

-- Index on Document year for temporal filtering
CREATE INDEX doc_year_index IF NOT EXISTS
  FOR (d:Document) ON (d.year);
```

---

## Design Rationale

This schema is intentionally climate-specific, not generic. Three design choices differentiate it from a plain document graph:

1. **Climate semantics are first-class nodes.** `ClimateRisk`, `ClimateTopic`, `Sector`, `Target`, and `Technology` are not tags or text fields — they are typed graph nodes with properties. This allows queries like "all technologies that mitigate risks occurring in the Middle East" without touching any PDF text.

2. **Findings anchor graph claims to pages.** Every `Finding` node stores the source `doc_id` and `page`. GraphRAG can retrieve a finding from the graph and immediately know which PDF page to fetch for the supporting chunk. This makes citation verification deterministic.

3. **Policies connect upward and downward.** A `Policy` node connects upward to `Country` and `Region`, and downward to `Target` and `ClimateTopic`. This enables the system to answer both "what has the UAE committed to?" (downward traversal) and "which countries have adopted net-zero policies?" (upward traversal from `Target`).
