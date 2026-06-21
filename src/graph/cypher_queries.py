"""Named Cypher queries for Rana's Climate Evidence Knowledge Graph notebook."""

CLIMATE_CYPHER_QUERIES = {
    "country_policies_targets": """
        MATCH (c:Country {country_id: $country_id})-[:HAS_POLICY]->(p:Policy)-[:SETS_TARGET]->(t:Target)
        RETURN c.name AS country, p.name AS policy, t.name AS target
        ORDER BY policy, target
    """,
    "risk_sector_region": """
        MATCH (risk:ClimateRisk)-[:IMPACTS]->(s:Sector)
        OPTIONAL MATCH (risk)-[:OCCURS_IN]->(r:Region)
        WHERE ($sector_id IS NULL OR s.sector_id = $sector_id)
          AND ($region_id IS NULL OR r.region_id = $region_id)
        RETURN risk.name AS risk, s.name AS sector, r.name AS region
        ORDER BY risk, sector
    """,
    "technology_evidence": """
        MATCH (d:Document)-[:MENTIONS_TECHNOLOGY]->(tech:Technology)
        WHERE $tech_id IS NULL OR tech.tech_id = $tech_id
        OPTIONAL MATCH (tech)-[:MITIGATES]->(risk:ClimateRisk)
        RETURN d.doc_id AS doc_id, d.title AS title, tech.name AS technology, risk.name AS mitigates
        ORDER BY technology, title
    """,
    "documents_for_topic": """
        MATCH (d:Document)-[:DISCUSSES]->(t:ClimateTopic {topic_id: $topic_id})
        RETURN d.doc_id AS doc_id, d.title AS title, d.year AS year
        ORDER BY d.year DESC
    """,
    "findings_with_indicators": """
        MATCH (d:Document)-[:REPORTS_FINDING]->(f:Finding)
        OPTIONAL MATCH (f)-[:EVIDENCES_RISK]->(risk:ClimateRisk)
        RETURN d.title AS source, f.text AS finding, risk.name AS indicator
        LIMIT 20
    """,
}


VALIDATION_QUERIES = {
    "validation_findings_missing_page": """
        MATCH (f:Finding)
        WHERE f.page IS NULL
        RETURN f.finding_id AS finding_id, f.doc_id AS doc_id, f.text AS text
    """,
    "validation_isolated_risks": """
        MATCH (r:ClimateRisk)
        WHERE NOT (r)--()
        RETURN r.risk_id AS risk_id, r.name AS risk
        ORDER BY risk
    """,
    "validation_high_cardinality_policy": """
        MATCH (p:Policy)<-[:HAS_POLICY]-(c:Country)
        WITH p, count(c) AS country_count
        WHERE country_count > 10
        RETURN p.name AS policy, country_count
        ORDER BY country_count DESC
    """,
    "validation_metadata_causal_edges": """
        MATCH ()-[r:IMPACTS|MITIGATES|OCCURS_IN]->()
        WHERE r.source = 'metadata'
        RETURN type(r) AS relationship, count(r) AS count
        ORDER BY relationship
    """,
}


GRAPHRAG_REASONING = {
    "graphrag_country_policy_target": """
        MATCH (c:Country {country_id: $country_id})-[:HAS_POLICY]->(p:Policy)-[:SETS_TARGET]->(t:Target)
        OPTIONAL MATCH (d:Document)-[:DISCUSSES_POLICY]->(p)
        RETURN c.name AS country,
               p.name AS policy,
               t.name AS target,
               d.doc_id AS doc_id,
               d.title AS source_doc,
               d.year AS doc_year
        ORDER BY policy, target, doc_year DESC
    """,
    "graphrag_policy_risk_sector": """
        MATCH (p:Policy {policy_id: $policy_id})-[:ADDRESSES]->(topic:ClimateTopic)-[:HAS_RISK]->(risk:ClimateRisk)
        OPTIONAL MATCH (risk)-[impact:IMPACTS]->(sector:Sector)
        OPTIONAL MATCH (d:Document)-[:DISCUSSES_POLICY]->(p)
        RETURN p.name AS policy,
               topic.name AS climate_topic,
               risk.name AS climate_risk,
               sector.name AS affected_sector,
               impact.confidence AS impact_confidence,
               impact.evidence_page AS evidence_page,
               d.doc_id AS doc_id,
               d.title AS source_doc
        ORDER BY climate_risk, affected_sector
    """,
    "graphrag_technology_mitigates_risk": """
        MATCH (tech:Technology)
        WHERE $tech_id IS NULL OR tech.tech_id = $tech_id
        OPTIONAL MATCH (tech)-[m:MITIGATES]->(risk:ClimateRisk)
        OPTIONAL MATCH (risk)-[:IMPACTS]->(sector:Sector)
        OPTIONAL MATCH (risk)-[:OCCURS_IN]->(region:Region)
        OPTIONAL MATCH (d:Document {doc_id: m.doc_id})
        RETURN tech.name AS technology,
               risk.name AS mitigated_risk,
               m.confidence AS mitigation_confidence,
               sector.name AS applicable_sector,
               region.name AS relevant_region,
               m.evidence_page AS evidence_page,
               d.doc_id AS doc_id,
               d.title AS source_doc,
               d.year AS source_year
        ORDER BY technology, mitigated_risk
    """,
    "graphrag_finding_document_grounding": """
        MATCH (f:Finding)-[:SUPPORTED_BY]->(d:Document)
        OPTIONAL MATCH (f)-[:EVIDENCES_RISK]->(risk:ClimateRisk)
        OPTIONAL MATCH (f)-[:EVIDENCES_SECTOR]->(sector:Sector)
        OPTIONAL MATCH (f)-[:EVIDENCES_COUNTRY]->(country:Country)
        OPTIONAL MATCH (f)-[:EVIDENCES_TECHNOLOGY]->(tech:Technology)
        OPTIONAL MATCH (d)-[:PUBLISHED_BY]->(org:Organization)
        WHERE ($risk_id IS NULL OR risk.risk_id = $risk_id)
          AND ($sector_id IS NULL OR sector.sector_id = $sector_id)
          AND ($country_id IS NULL OR country.country_id = $country_id)
          AND ($tech_id IS NULL OR tech.tech_id = $tech_id)
          AND ($confidence_levels IS NULL OR f.confidence IN $confidence_levels)
        RETURN f.text AS evidence_text,
               f.page AS page,
               f.confidence AS confidence,
               f.qdrant_chunk_id AS qdrant_chunk_id,
               d.doc_id AS doc_id,
               d.doc_type AS doc_type,
               org.name AS publisher,
               d.year AS doc_year
        ORDER BY f.confidence_rank DESC, d.year DESC
    """,
    "graphrag_region_climate_risk": """
        MATCH (region:Region {region_id: $region_id})<-[:LOCATED_IN]-(country:Country)
        OPTIONAL MATCH (country)-[:HAS_POLICY]->(policy:Policy)
        OPTIONAL MATCH (risk:ClimateRisk)-[occurs:OCCURS_IN]->(region)
        OPTIONAL MATCH (risk)-[impact:IMPACTS]->(sector:Sector)
        OPTIONAL MATCH (d:Document {doc_id: coalesce(occurs.doc_id, impact.doc_id)})
        RETURN region.name AS region,
               risk.name AS climate_risk,
               sector.name AS impacted_sector,
               occurs.confidence AS risk_occurrence_confidence,
               country.name AS country,
               policy.name AS relevant_policy,
               coalesce(occurs.evidence_page, impact.evidence_page) AS evidence_page,
               d.doc_id AS doc_id,
               d.title AS source_doc
        ORDER BY climate_risk, impacted_sector, relevant_policy
    """,
}


GRAPH_STATISTICS = {
    "stats_graph_density": """
        MATCH (n)
        WITH count(n) AS nodes
        MATCH ()-[r]->()
        RETURN nodes, count(r) AS relationships,
               CASE WHEN nodes = 0 THEN 0.0 ELSE toFloat(count(r)) / nodes END AS avg_relationships_per_node
    """,
    "stats_finding_coverage": """
        MATCH (d:Document)
        OPTIONAL MATCH (d)-[:REPORTS_FINDING]->(f:Finding)
        RETURN count(DISTINCT d) AS documents,
               count(f) AS findings,
               count(DISTINCT CASE WHEN f IS NOT NULL THEN d END) AS documents_with_findings
    """,
    "stats_technology_coverage": """
        MATCH (t:Technology)
        OPTIONAL MATCH (t)-[:MITIGATES]->(r:ClimateRisk)
        RETURN count(DISTINCT t) AS technologies,
               count(DISTINCT CASE WHEN r IS NOT NULL THEN t END) AS technologies_with_mitigation_edges
    """,
    "stats_risk_coverage": """
        MATCH (r:ClimateRisk)
        OPTIONAL MATCH (r)-[:IMPACTS]->(s:Sector)
        RETURN count(DISTINCT r) AS risks,
               count(DISTINCT CASE WHEN s IS NOT NULL THEN r END) AS risks_with_sector_impacts
    """,
    "stats_country_policy_coverage": """
        MATCH (c:Country)
        OPTIONAL MATCH (c)-[:HAS_POLICY]->(p:Policy)
        RETURN count(DISTINCT c) AS countries,
               count(DISTINCT CASE WHEN p IS NOT NULL THEN c END) AS countries_with_policies
    """,
}


_ALL_QUERIES = {
    **CLIMATE_CYPHER_QUERIES,
    **VALIDATION_QUERIES,
    **GRAPHRAG_REASONING,
    **GRAPH_STATISTICS,
}


def get_query(name: str) -> str:
    try:
        return _ALL_QUERIES[name]
    except KeyError as exc:
        available = ", ".join(sorted(_ALL_QUERIES))
        raise KeyError(f"Unknown Cypher query {name!r}. Available queries: {available}") from exc


def list_queries(prefix: str | None = None) -> list[str]:
    names = sorted(_ALL_QUERIES)
    if prefix:
        names = [name for name in names if name.startswith(prefix)]
    return names
