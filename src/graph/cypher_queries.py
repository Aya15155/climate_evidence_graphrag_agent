# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: keep this graph climate-specific; do not reduce it to only Paper/Author/Topic.
# - Improvement: add more relationship extraction rules from metadata and validated PDF evidence.
# - Improvement: add Cypher queries for UAE policy targets, risk-sector impact, technology mitigation, and evidence-supported findings.
# ------------------------------------------------------------
CLIMATE_CYPHER_QUERIES = {
    "country_policies_targets": """
        MATCH (c:Country {name: $country})-[:HAS_POLICY]->(p:Policy)-[:SETS_TARGET]->(t:Target)
        RETURN c.name AS country, p.name AS policy, t.name AS target
    """,
    "risk_sector_region": """
        MATCH (risk:ClimateRisk)-[:IMPACTS]->(s:Sector)
        OPTIONAL MATCH (risk)-[:OCCURS_IN]->(r:Region)
        WHERE s.name = $sector OR r.name = $region
        RETURN risk.name AS risk, s.name AS sector, r.name AS region
    """,
    "technology_evidence": """
        MATCH (d:Document)-[:MENTIONS_TECHNOLOGY]->(tech:Technology {name: $technology})
        OPTIONAL MATCH (tech)-[:MITIGATES]->(risk:ClimateRisk)
        RETURN d.document_id AS document_id, d.title AS title, tech.name AS technology, risk.name AS mitigates
    """,
    "documents_for_topic": """
        MATCH (d:Document)-[:DISCUSSES]->(t:ClimateTopic {name: $topic})
        RETURN d.document_id AS document_id, d.title AS title, d.year AS year
        ORDER BY d.year DESC
    """,
    "findings_with_indicators": """
        MATCH (d:Document)-[:REPORTS_FINDING]->(f:Finding)-[:HAS_INDICATOR]->(i:Indicator)
        RETURN d.title AS source, f.text AS finding, i.name AS indicator
        LIMIT 20
    """,
}


def get_query(name: str) -> str:
    return CLIMATE_CYPHER_QUERIES[name]
