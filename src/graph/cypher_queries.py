"""Named Cypher queries for Rana's Climate Evidence Knowledge Graph notebook.

Changelog vs previous version
-------------------------------
Q1  graphrag_country_policy_target  — removed DISCUSSES_POLICY Cartesian join;
    now routes evidence through REPORTS_FINDING → EVIDENCES_COUNTRY to keep
    source_doc constrained to country-relevant documents only.

Q2  graphrag_policy_risk_sector     — entry MATCH now accepts policy_id OR a
    fuzzy policy_name substring so slug-mismatch no longer silently returns
    nothing; removed DISCUSSES_POLICY join; routes evidence through
    REPORTS_FINDING → EVIDENCES_RISK.

Q3  graphrag_technology_mitigates_risk — unchanged structurally; relies on
    real MITIGATES edges once demo findings are deleted.

Q4  graphrag_finding_document_grounding — now checks EITHER REPORTS_FINDING
    OR SUPPORTED_BY so both edge styles pass integrity validation.

Q5  graphrag_region_climate_risk     — entry MATCH now accepts region_id,
    aliases array, or a fuzzy region_name substring; adds region_name param.

Validation
-----------
validation_finding_not_linked  — updated to check EITHER relationship type so
    the 6-FAIL integrity-check false positive is eliminated.
"""

# ---------------------------------------------------------------------------
# Basic convenience queries
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Validation queries
# ---------------------------------------------------------------------------
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
    # FIX (Problem 5): accept EITHER REPORTS_FINDING or SUPPORTED_BY so both
    # edge styles pass the integrity check without false 6-FAIL results.
    "validation_finding_not_linked": """
        MATCH (f:Finding)
        WHERE NOT (:Document)-[:REPORTS_FINDING]->(f)
          AND NOT (f)-[:SUPPORTED_BY]->(:Document)
        RETURN count(f) AS unlinked_findings
    """,
    # Audit helpers — run these in Neo4j Browser to expose slug mismatches
    # before calling any GraphRAG reasoning query.
    "audit_region_ids": """
        MATCH (r:Region) RETURN r.region_id, r.name ORDER BY r.name
    """,
    "audit_policy_ids": """
        MATCH (p:Policy) RETURN p.policy_id, p.name, p.status ORDER BY p.name
    """,
    "audit_tech_ids": """
        MATCH (t:Technology) RETURN t.tech_id, t.name ORDER BY t.name
    """,
    "audit_country_ids": """
        MATCH (c:Country) RETURN c.country_id, c.name ORDER BY c.name
    """,
    # Cleanup — run once to remove nan/null placeholder nodes left by
    # unguarded NaN values passed through split_and_normalize().
    "cleanup_nan_nodes": """
        MATCH (n)
        WHERE n.name = 'nan' OR n.name IS NULL
        DETACH DELETE n
    """,
    # Cleanup — remove all demo findings and their derived causal edges.
    # After this runs, MITIGATES and IMPACTS counts will reflect only
    # real PDF-extracted evidence.
    "cleanup_demo_findings": """
        MATCH (f:Finding)
        WHERE f.finding_id STARTS WITH 'd2_demo_finding_'
           OR f.extraction_method = 'demo'
        DETACH DELETE f
    """,
}

# ---------------------------------------------------------------------------
# GraphRAG reasoning queries (five core traversals)
# ---------------------------------------------------------------------------
GRAPHRAG_REASONING = {
    # ------------------------------------------------------------------
    # Q1 — Country → Policy → Target with page-anchored source docs
    #
    # FIX (Problem 1): removed DISCUSSES_POLICY join that caused a
    # Cartesian explosion (405 rows from 3 policy-target pairs).
    # Source documents are now constrained via
    # REPORTS_FINDING → EVIDENCES_COUNTRY so only country-relevant docs
    # appear in source_doc.
    #
    # Parameters: $country_id (required)
    # ------------------------------------------------------------------
    "graphrag_country_policy_target": """
        MATCH (c:Country {country_id: $country_id})
              -[:HAS_POLICY]->(p:Policy)
              -[:SETS_TARGET]->(t:Target)
        WHERE p.status = 'adopted' OR p.status IS NULL
        OPTIONAL MATCH (d:Document)-[:REPORTS_FINDING]->(f:Finding)
                       -[:EVIDENCES_COUNTRY]->(c)
        WITH c, p, t, d, f
        ORDER BY
            CASE p.status WHEN 'adopted' THEN 0 ELSE 1 END,
            t.target_year ASC
        RETURN c.name             AS country,
               p.name             AS policy,
               p.policy_type      AS policy_type,
               t.name             AS target,
               t.value            AS target_value,
               t.target_year      AS deadline,
               d.title            AS source_doc,
               f.page             AS evidence_page,
               f.confidence       AS confidence
        ORDER BY
            CASE p.status WHEN 'adopted' THEN 0 ELSE 1 END,
            t.target_year ASC
    """,

    # ------------------------------------------------------------------
    # Q2 — Policy → ClimateTopic → ClimateRisk → Sector
    #
    # FIX (Problem 2): entry MATCH now matches by policy_id OR a
    # case-insensitive substring of policy_name so slug mismatches
    # (e.g. 'uae_net_zero_by_2050' not found) no longer return nothing
    # silently.  Also removed DISCUSSES_POLICY join; evidence now comes
    # from REPORTS_FINDING → EVIDENCES_RISK.
    #
    # Parameters: $policy_id (required), $policy_name (optional fuzzy)
    # ------------------------------------------------------------------
    "graphrag_policy_risk_sector": """
        MATCH (p:Policy)
        WHERE p.policy_id = $policy_id
           OR ($policy_name IS NOT NULL
               AND toLower(p.name) CONTAINS toLower($policy_name))
        MATCH (p)-[:ADDRESSES]->(topic:ClimateTopic)
              -[:HAS_RISK]->(risk:ClimateRisk)
        OPTIONAL MATCH (risk)-[impact:IMPACTS]->(sector:Sector)
        WHERE impact.confidence IN ['high', 'medium'] OR impact IS NULL
        OPTIONAL MATCH (d:Document)-[:REPORTS_FINDING]->(f:Finding)
                       -[:EVIDENCES_RISK]->(risk)
        RETURN p.name             AS policy,
               topic.name         AS climate_topic,
               risk.name          AS climate_risk,
               sector.name        AS affected_sector,
               impact.confidence  AS impact_confidence,
               f.page             AS evidence_page,
               d.title            AS source_doc
        ORDER BY climate_risk, affected_sector
    """,

    # ------------------------------------------------------------------
    # Q3 — Technology → ClimateRisk → Sector / Region
    #
    # Unchanged structurally.  Will return meaningful results once demo
    # findings are deleted and real MITIGATES edges are populated.
    #
    # Parameters: $tech_id (optional; NULL returns all technologies)
    # ------------------------------------------------------------------
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
               d.title AS source_doc,
               d.year AS source_year
        ORDER BY technology, mitigated_risk
    """,

    # ------------------------------------------------------------------
    # Q4 — Finding ↔ Document grounding with evidence filters
    #
    # FIX (Problem 5): MATCH now accepts findings linked via EITHER
    # (Document)-[:REPORTS_FINDING]->(Finding) or
    # (Finding)-[:SUPPORTED_BY]->(Document) so both relationship styles
    # resolve correctly.
    #
    # Parameters: $risk_id, $sector_id, $country_id, $tech_id,
    #             $confidence_levels — all optional (NULL = no filter)
    # ------------------------------------------------------------------
    "graphrag_finding_document_grounding": """
        MATCH (f:Finding)
        WHERE (:Document)-[:REPORTS_FINDING]->(f)
           OR (f)-[:SUPPORTED_BY]->(:Document)
        OPTIONAL MATCH (d:Document)-[:REPORTS_FINDING]->(f)
        OPTIONAL MATCH (f)-[:SUPPORTED_BY]->(d2:Document)
        WITH f, coalesce(d, d2) AS doc
        OPTIONAL MATCH (f)-[:EVIDENCES_RISK]->(risk:ClimateRisk)
        OPTIONAL MATCH (f)-[:EVIDENCES_SECTOR]->(sector:Sector)
        OPTIONAL MATCH (f)-[:EVIDENCES_COUNTRY]->(country:Country)
        OPTIONAL MATCH (f)-[:EVIDENCES_TECHNOLOGY]->(tech:Technology)
        OPTIONAL MATCH (doc)-[:PUBLISHED_BY]->(org:Organization)
        WHERE ($risk_id IS NULL OR risk.risk_id = $risk_id)
          AND ($sector_id IS NULL OR sector.sector_id = $sector_id)
          AND ($country_id IS NULL OR country.country_id = $country_id)
          AND ($tech_id IS NULL OR tech.tech_id = $tech_id)
          AND ($confidence_levels IS NULL OR f.confidence IN $confidence_levels)
        RETURN f.text AS evidence_text,
               f.page AS page,
               f.confidence AS confidence,
               f.qdrant_chunk_id AS qdrant_chunk_id,
               doc.doc_id AS doc_id,
               doc.doc_type AS doc_type,
               org.name AS publisher,
               doc.year AS doc_year
        ORDER BY f.confidence_rank DESC, doc.year DESC
    """,

    # ------------------------------------------------------------------
    # Q5 — Region → ClimateRisk → Sector / Country / Policy
    #
    # FIX (Problem 3): entry MATCH now resolves the Region node by
    # region_id OR aliases array OR a case-insensitive substring of
    # region_name so slug mismatches (e.g. 'middle_east_and_north_africa'
    # vs stored 'mena') no longer cause silent empty results.
    #
    # Parameters: $region_id (required), $region_name (optional fuzzy)
    # ------------------------------------------------------------------
    "graphrag_region_climate_risk": """
        MATCH (region:Region)
        WHERE region.region_id = $region_id
           OR ($region_id IN region.aliases)
           OR ($region_name IS NOT NULL
               AND toLower(region.name) CONTAINS toLower($region_name))
        OPTIONAL MATCH (region)<-[:LOCATED_IN]-(country:Country)
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
               d.title AS source_doc
        ORDER BY climate_risk, impacted_sector, relevant_policy
    """,
}

# ---------------------------------------------------------------------------
# Graph statistics queries
# ---------------------------------------------------------------------------
GRAPH_STATISTICS = {
    "stats_graph_density": """
        MATCH (n)
        WITH count(n) AS nodes
        MATCH ()-[r]->()
        RETURN nodes, count(r) AS relationships,
               CASE WHEN nodes = 0 THEN 0.0
                    ELSE toFloat(count(r)) / nodes END AS avg_relationships_per_node
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

# ---------------------------------------------------------------------------
# One-time repair Cypher — run these in Neo4j Browser in the order listed
# ---------------------------------------------------------------------------
ONE_TIME_REPAIRS = {
    # Step 1 — normalise a MENA Region node to a consistent slug + aliases
    "repair_mena_region_slug": """
        MATCH (r:Region)
        WHERE r.name IN ['MENA', 'Middle East', 'ME', 'Middle East and North Africa']
        SET r.region_id  = 'mena',
            r.name       = 'Middle East and North Africa',
            r.aliases    = ['mena', 'middle_east', 'middle_east_and_north_africa', 'me']
    """,
    # Step 2 — consolidate fragmented Technology nodes for 'battery storage'
    "repair_battery_storage_node": """
        MATCH (old:Technology {name: 'battery storage'})
        MERGE (new:Technology {name: 'Battery Energy Storage Systems'})
            ON CREATE SET new.tech_id = 'battery_energy_storage_systems'
        WITH old, new
        OPTIONAL MATCH (old)-[r:MITIGATES]->(x)
        FOREACH (_ IN CASE WHEN x IS NOT NULL THEN [1] ELSE [] END |
            MERGE (new)-[:MITIGATES]->(x)
        )
        DETACH DELETE old
    """,
    # Step 3 — consolidate fragmented Technology nodes for 'carbon capture'
    "repair_carbon_capture_node": """
        MATCH (old:Technology {name: 'carbon capture'})
        MERGE (new:Technology {name: 'Carbon Capture and Storage'})
            ON CREATE SET new.tech_id = 'carbon_capture_and_storage'
        WITH old, new
        OPTIONAL MATCH (old)-[r:MITIGATES]->(x)
        FOREACH (_ IN CASE WHEN x IS NOT NULL THEN [1] ELSE [] END |
            MERGE (new)-[:MITIGATES]->(x)
        )
        DETACH DELETE old
    """,
}

# ---------------------------------------------------------------------------
# Unified lookup dict
# ---------------------------------------------------------------------------
_ALL_QUERIES = {
    **CLIMATE_CYPHER_QUERIES,
    **VALIDATION_QUERIES,
    **GRAPHRAG_REASONING,
    **GRAPH_STATISTICS,
    **ONE_TIME_REPAIRS,
}


def get_query(name: str) -> str:
    """Return a named Cypher query string.

    Raises KeyError with a list of available names if *name* is not found.
    """
    try:
        return _ALL_QUERIES[name]
    except KeyError as exc:
        available = ", ".join(sorted(_ALL_QUERIES))
        raise KeyError(
            f"Unknown Cypher query {name!r}. Available queries: {available}"
        ) from exc


def list_queries(prefix: str | None = None) -> list[str]:
    """Return sorted query names, optionally filtered by *prefix*."""
    names = sorted(_ALL_QUERIES)
    if prefix:
        names = [n for n in names if n.startswith(prefix)]
    return names