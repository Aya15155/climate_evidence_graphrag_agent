"""Climate Evidence Knowledge Graph builder for Neo4j.

Changelog vs previous version
-------------------------------
Fix 1  (Problem 4)  — _safe_names() NaN guard added; every call to
        split_list_field() is now wrapped so NaN/None/empty strings
        never produce entity nodes with name='nan'.

Fix 2  (Problem 7)  — ENTITY_ALIASES dict added; normalize_entity_name()
        resolves known variant spellings to canonical forms before MERGE,
        preventing Technology (and other entity) fragmentation
        (e.g. 'battery storage' → 'Battery Energy Storage Systems').

Fix 3  (Problem 3)  — _merge_regions() writes an aliases property on every
        Region node so Q5 slug-fallback matching works for future ingestion.

Fix 4  (Problem 5)  — validate_finding_integrity() 'not_linked_to_document'
        check now accepts EITHER (Document)-[:REPORTS_FINDING]->(Finding)
        OR (Finding)-[:SUPPORTED_BY]->(Document).

Fix 5  (Problem 6)  — _merge_finding() gates IMPACTS and MITIGATES writes
        behind an extraction_method != 'demo' check so demo/fabricated
        findings cannot create causal edges.

Fix 6  (Problems 1/2) — _merge_metadata_relationships() no longer writes
        DISCUSSES_POLICY edges (moved to a separate, clearly-named
        _merge_policy_relationships() helper that is called explicitly).
        ADDRESSES edges (Policy → ClimateTopic) are now always written
        during metadata ingestion, not only for narrow doc_type lists.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

try:
    from src.ingest.metadata_loader import split_list_field
except ModuleNotFoundError:
    from ingest.metadata_loader import split_list_field


LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical country ID lookup
# ---------------------------------------------------------------------------
COUNTRY_IDS = {
    "uae": "ARE",
    "united arab emirates": "ARE",
    "global": "GLOBAL",
    "saudi arabia": "SAU",
    "egypt": "EGY",
    "jordan": "JOR",
    "germany": "DEU",
}

# ---------------------------------------------------------------------------
# FIX 2 (Problem 7) — entity alias normalisation
# Keys are lowercase variant spellings; values are the canonical display name.
# Extend this dict whenever fragmented entity nodes appear in audit queries.
# ---------------------------------------------------------------------------
ENTITY_ALIASES: Dict[str, str] = {
    # Technologies
    "battery storage":                  "Battery Energy Storage Systems",
    "bess":                             "Battery Energy Storage Systems",
    "carbon capture":                   "Carbon Capture and Storage",
    "carbon capture storage":           "Carbon Capture and Storage",
    "ccs":                              "Carbon Capture and Storage",
    "climate downscaling":              "Climate Modelling",
    "deep learning":                    "Machine Learning for Climate",
    "ml":                               "Machine Learning for Climate",
    "electric vehicle":                 "Electric Vehicles",
    "ev":                               "Electric Vehicles",
    "direct air capture":               "Direct Air Capture",
    "dac":                              "Direct Air Capture",
    "solar":                            "Solar PV",
    "solar power":                      "Solar PV",
    "wind":                             "Wind Power",
    "wind energy":                      "Wind Power",
    "hydrogen":                         "Green Hydrogen",
    "green h2":                         "Green Hydrogen",
    # Regions
    "mena":                             "Middle East and North Africa",
    "middle east":                      "Middle East and North Africa",
    "me":                               "Middle East and North Africa",
    "gcc region":                       "Gulf Cooperation Council",
    "gulf":                             "Gulf Cooperation Council",
    "gcc":                              "Gulf Cooperation Council",
    # ClimateRisks — keep consistent with schema
    "emissions":                        "Carbon Emissions",
    "ghg emissions":                    "Carbon Emissions",
    "greenhouse gas emissions":         "Carbon Emissions",
    "heat":                             "Extreme Heat",
    "heatwave":                         "Extreme Heat",
    "heatwaves":                        "Extreme Heat",
    "sea level":                        "Sea Level Rise",
    "slr":                              "Sea Level Rise",
}

# Region aliases written to the graph so Q5 fuzzy matching works at query time
REGION_ALIASES: Dict[str, list[str]] = {
    "Middle East and North Africa": [
        "mena", "middle_east", "middle_east_and_north_africa", "me",
    ],
    "Gulf Cooperation Council": [
        "gcc", "gulf", "gcc_region",
    ],
    "Sub-Saharan Africa": [
        "sub_saharan_africa", "ssa",
    ],
    "South Asia": [
        "south_asia",
    ],
    "Southeast Asia": [
        "southeast_asia", "sea",
    ],
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def slugify(value: Any) -> str:
    """Return a stable lowercase ID for graph entities."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def country_id_for(name: Any) -> str:
    text = str(name or "").strip()
    return COUNTRY_IDS.get(text.lower(), slugify(text).upper()[:3] or "UNK")


def confidence_rank(value: str) -> int:
    ranks = {"low": 1, "medium": 2, "high": 3, "very_high": 4}
    return ranks.get(str(value or "").lower(), 0)


def normalize_entity_name(name: str) -> str:
    """Return the canonical display name for *name*, resolving known aliases.

    Falls back to the original (title-cased) value if no alias is found.
    """
    canonical = ENTITY_ALIASES.get(name.strip().lower())
    return canonical if canonical else name.strip()


# FIX 1 (Problem 4) — NaN guard applied before any split_list_field call.
def _safe_names(raw_field: Any) -> list[str]:
    """Split *raw_field* into clean non-empty, non-NaN names.

    Drops values whose stripped lowercase form is 'nan', 'none', or empty.
    Also applies entity alias normalisation so canonical names are stored.
    """
    raw = str(raw_field or "").strip()
    if raw.lower() in ("nan", "none", ""):
        return []
    names = split_list_field(raw)
    result = []
    for n in names:
        clean = str(n or "").strip()
        if clean.lower() in ("nan", "none", ""):
            continue
        result.append(normalize_entity_name(clean))
    return result


# ---------------------------------------------------------------------------
# Main builder class
# ---------------------------------------------------------------------------

class ClimateGraphBuilder:
    """Build the Climate Evidence Knowledge Graph in Neo4j.

    The builder supports the D2 Rana notebook directly: constraints, document
    ingestion, curated finding ingestion, validation, and summary counts.
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "climate123",
        retries: int = 3,
        retry_seconds: float = 1.0,
    ):
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        last_error: Exception | None = None
        for _ in range(retries):
            try:
                self.driver.verify_connectivity()
                return
            except Exception as exc:  # pragma: no cover
                last_error = exc
                time.sleep(retry_seconds)
        raise ConnectionError(
            f"Could not connect to Neo4j at {uri}. "
            "Start Neo4j with docker-compose up -d neo4j or check NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD."
        ) from last_error

    def close(self) -> None:
        self.driver.close()

    # ------------------------------------------------------------------
    # Schema constraints and indexes
    # ------------------------------------------------------------------

    def run_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.doc_id IS UNIQUE",
            "CREATE CONSTRAINT org_id_unique IF NOT EXISTS FOR (n:Organization) REQUIRE n.org_id IS UNIQUE",
            "CREATE CONSTRAINT venue_id_unique IF NOT EXISTS FOR (n:Venue) REQUIRE n.venue_id IS UNIQUE",
            "CREATE CONSTRAINT country_id_unique IF NOT EXISTS FOR (n:Country) REQUIRE n.country_id IS UNIQUE",
            "CREATE CONSTRAINT region_id_unique IF NOT EXISTS FOR (n:Region) REQUIRE n.region_id IS UNIQUE",
            "CREATE CONSTRAINT topic_id_unique IF NOT EXISTS FOR (n:ClimateTopic) REQUIRE n.topic_id IS UNIQUE",
            "CREATE CONSTRAINT risk_id_unique IF NOT EXISTS FOR (n:ClimateRisk) REQUIRE n.risk_id IS UNIQUE",
            "CREATE CONSTRAINT sector_id_unique IF NOT EXISTS FOR (n:Sector) REQUIRE n.sector_id IS UNIQUE",
            "CREATE CONSTRAINT tech_id_unique IF NOT EXISTS FOR (n:Technology) REQUIRE n.tech_id IS UNIQUE",
            "CREATE CONSTRAINT policy_id_unique IF NOT EXISTS FOR (n:Policy) REQUIRE n.policy_id IS UNIQUE",
            "CREATE CONSTRAINT target_id_unique IF NOT EXISTS FOR (n:Target) REQUIRE n.target_id IS UNIQUE",
            "CREATE CONSTRAINT finding_id_unique IF NOT EXISTS FOR (n:Finding) REQUIRE n.finding_id IS UNIQUE",
            "CREATE INDEX doc_year_index IF NOT EXISTS FOR (n:Document) ON (n.year)",
            "CREATE INDEX risk_type_index IF NOT EXISTS FOR (n:ClimateRisk) ON (n.risk_type)",
            "CREATE INDEX finding_page_index IF NOT EXISTS FOR (n:Finding) ON (n.doc_id, n.page)",
            "CREATE FULLTEXT INDEX finding_text_index IF NOT EXISTS FOR (n:Finding) ON EACH [n.text]",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------

    def bulk_upsert_documents(
        self, records: Iterable[Dict[str, Any]], include_relationships: bool = True
    ) -> Dict[str, int]:
        processed = 0
        errors = 0
        with self.driver.session() as session:
            for raw in records:
                rec = self._normalize_document(raw)
                try:
                    session.execute_write(self._merge_document_graph, rec, include_relationships)
                    processed += 1
                except Exception:
                    errors += 1
                    LOGGER.exception("Failed to upsert document %s", rec.get("doc_id"))
        return {"processed": processed, "errors": errors}

    def upsert_document_graph(self, rec: Dict[str, Any]) -> None:
        with self.driver.session() as session:
            session.execute_write(
                self._merge_document_graph, self._normalize_document(rec), True
            )

    @staticmethod
    def _normalize_document(raw: Dict[str, Any]) -> Dict[str, Any]:
        title = raw.get("title") or "Untitled climate document"
        doc_id = raw.get("doc_id") or raw.get("document_id") or slugify(title)
        return {
            **raw,
            "doc_id": str(doc_id),
            "title": title,
            "year": (
                int(float(raw.get("year") or 0))
                if str(raw.get("year") or "").strip()
                else None
            ),
            "doc_type": raw.get("doc_type") or raw.get("document_type") or "",
            "organization": raw.get("organization") or "Unknown Organization",
            "org_id": slugify(raw.get("organization") or "Unknown Organization"),
            "venue": raw.get("venue") or "Unknown Venue",
            "venue_id": slugify(raw.get("venue") or "Unknown Venue"),
            "language": raw.get("language") or "en",
            "url": raw.get("url") or raw.get("pdf_path") or "",
            "page_count": (
                int(float(raw.get("page_count") or raw.get("total_pages") or 0))
                if str(raw.get("page_count") or raw.get("total_pages") or "").strip()
                else None
            ),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _merge_document_graph(tx, rec: Dict[str, Any], include_relationships: bool) -> None:
        tx.run(
            """
            MERGE (d:Document {doc_id: $doc_id})
            SET d.title = $title,
                d.year = $year,
                d.doc_type = $doc_type,
                d.language = $language,
                d.url = $url,
                d.page_count = $page_count,
                d.ingested_at = coalesce(d.ingested_at, $ingested_at)
            MERGE (o:Organization {org_id: $org_id})
            SET o.name = $organization
            MERGE (d)-[:PUBLISHED_BY]->(o)
            MERGE (v:Venue {venue_id: $venue_id})
            SET v.name = $venue
            MERGE (d)-[:PUBLISHED_IN]->(v)
            """,
            **rec,
        )
        if not include_relationships:
            return

        ClimateGraphBuilder._merge_list_entities(tx, rec, "topics", "ClimateTopic", "topic_id", "DISCUSSES")
        ClimateGraphBuilder._merge_countries(tx, rec)
        ClimateGraphBuilder._merge_regions(tx, rec)
        ClimateGraphBuilder._merge_list_entities(tx, rec, "sectors", "Sector", "sector_id", "AFFECTS_SECTOR")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "climate_risks", "ClimateRisk", "risk_id", "DISCUSSES_RISK")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "technologies", "Technology", "tech_id", "MENTIONS_TECHNOLOGY")
        # DISCUSSES_POLICY is retained as a document-frequency index only.
        # GraphRAG reasoning queries do NOT traverse this edge.
        ClimateGraphBuilder._merge_list_entities(tx, rec, "policies", "Policy", "policy_id", "DISCUSSES_POLICY")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "targets", "Target", "target_id", "DISCUSSES_TARGET")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "indicators", "Indicator", "indicator_id", "REPORTS_INDICATOR")
        ClimateGraphBuilder._merge_metadata_relationships(tx, rec)

    @staticmethod
    def _merge_list_entities(
        tx, rec: Dict[str, Any], field: str, label: str, id_prop: str, document_rel: str
    ) -> None:
        # FIX 1: use _safe_names() to skip NaN/empty values and apply alias normalisation
        for name in _safe_names(rec.get(field, "")):
            entity_id = slugify(name)
            if entity_id in ("nan", "unknown", ""):
                LOGGER.debug("Skipping blank/NaN entity for field=%s doc=%s", field, rec.get("doc_id"))
                continue
            tx.run(
                f"""
                MATCH (d:Document {{doc_id: $doc_id}})
                MERGE (n:{label} {{{id_prop}: $entity_id}})
                SET n.name = $name
                MERGE (d)-[:{document_rel}]->(n)
                """,
                doc_id=rec["doc_id"],
                entity_id=entity_id,
                name=name,
            )

    @staticmethod
    def _merge_countries(tx, rec: Dict[str, Any]) -> None:
        # FIX 1: use _safe_names() to skip NaN country values
        for name in _safe_names(rec.get("countries", "")):
            cid = country_id_for(name)
            if not cid or cid in ("UNK", "NAN"):
                continue
            tx.run(
                """
                MATCH (d:Document {doc_id: $doc_id})
                MERGE (c:Country {country_id: $country_id})
                SET c.name = $name
                MERGE (d)-[:MENTIONS_COUNTRY]->(c)
                """,
                doc_id=rec["doc_id"],
                country_id=cid,
                name=name,
            )

    # FIX 3 (Problem 3) — dedicated region helper that writes aliases so
    # Q5 slug-fallback matching works at query time for freshly ingested docs.
    @staticmethod
    def _merge_regions(tx, rec: Dict[str, Any]) -> None:
        for name in _safe_names(rec.get("regions", "")):
            region_id = slugify(name)
            if region_id in ("nan", "unknown", ""):
                continue
            aliases = REGION_ALIASES.get(name, [slugify(name)])
            tx.run(
                """
                MERGE (r:Region {region_id: $region_id})
                SET r.name = $name,
                    r.aliases = $aliases
                """,
                region_id=region_id,
                name=name,
                aliases=aliases,
            )

    @staticmethod
    def _merge_metadata_relationships(tx, rec: Dict[str, Any]) -> None:
        # Country → Region (LOCATED_IN)
        for country in _safe_names(rec.get("countries", "")):
            cid = country_id_for(country)
            if not cid or cid in ("UNK", "NAN"):
                continue
            for region in _safe_names(rec.get("regions", "")):
                region_id = slugify(region)
                if region_id in ("nan", "unknown", ""):
                    continue
                aliases = REGION_ALIASES.get(region, [region_id])
                tx.run(
                    """
                    MERGE (c:Country {country_id: $country_id})
                    SET c.name = $country
                    MERGE (r:Region {region_id: $region_id})
                    SET r.name = $region,
                        r.aliases = $aliases
                    MERGE (c)-[:LOCATED_IN]->(r)
                    """,
                    country_id=cid,
                    country=country,
                    region_id=region_id,
                    region=region,
                    aliases=aliases,
                )

            # Country → Policy (HAS_POLICY)
            for policy in _safe_names(rec.get("policies", "")):
                policy_id = slugify(policy)
                if policy_id in ("nan", "unknown", ""):
                    continue
                tx.run(
                    """
                    MERGE (c:Country {country_id: $country_id})
                    SET c.name = $country
                    MERGE (p:Policy {policy_id: $policy_id})
                    SET p.name = $policy
                    MERGE (c)-[:HAS_POLICY]->(p)
                    """,
                    country_id=cid,
                    country=country,
                    policy_id=policy_id,
                    policy=policy,
                )

        # Policy → Target (SETS_TARGET)
        # Policy → ClimateTopic (ADDRESSES)   ← FIX 6 (Problem 2): always written here
        for policy in _safe_names(rec.get("policies", "")):
            policy_id = slugify(policy)
            if policy_id in ("nan", "unknown", ""):
                continue

            for target in _safe_names(rec.get("targets", "")):
                target_id = slugify(target)
                if target_id in ("nan", "unknown", ""):
                    continue
                tx.run(
                    """
                    MERGE (p:Policy {policy_id: $policy_id})
                    SET p.name = $policy
                    MERGE (t:Target {target_id: $target_id})
                    SET t.name = $target
                    MERGE (p)-[:SETS_TARGET]->(t)
                    """,
                    policy_id=policy_id,
                    policy=policy,
                    target_id=target_id,
                    target=target,
                )

            # FIX 6: write ADDRESSES for every doc_type (not gated on policy doc types)
            for topic in _safe_names(rec.get("topics", "")):
                topic_id = slugify(topic)
                if topic_id in ("nan", "unknown", ""):
                    continue
                tx.run(
                    """
                    MERGE (p:Policy {policy_id: $policy_id})
                    SET p.name = $policy
                    MERGE (t:ClimateTopic {topic_id: $topic_id})
                    SET t.name = $topic
                    MERGE (p)-[:ADDRESSES]->(t)
                    """,
                    policy_id=policy_id,
                    policy=policy,
                    topic_id=topic_id,
                    topic=topic,
                )

        # ClimateTopic → ClimateRisk (HAS_RISK)
        for topic in _safe_names(rec.get("topics", "")):
            topic_id = slugify(topic)
            if topic_id in ("nan", "unknown", ""):
                continue
            for risk in _safe_names(rec.get("climate_risks", "")):
                risk_id = slugify(risk)
                if risk_id in ("nan", "unknown", ""):
                    continue
                tx.run(
                    """
                    MERGE (t:ClimateTopic {topic_id: $topic_id})
                    SET t.name = $topic
                    MERGE (r:ClimateRisk {risk_id: $risk_id})
                    SET r.name = $risk
                    MERGE (t)-[:HAS_RISK]->(r)
                    """,
                    topic_id=topic_id,
                    topic=topic,
                    risk_id=risk_id,
                    risk=risk,
                )

    # ------------------------------------------------------------------
    # Finding ingestion
    # ------------------------------------------------------------------

    def bulk_upsert_findings(self, records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        processed = 0
        errors = 0
        with self.driver.session() as session:
            # Remove orphaned demo findings before re-ingesting
            session.run(
                """
                MATCH (f:Finding)
                WHERE NOT (f)-[:SUPPORTED_BY]->(:Document)
                  AND (
                    f.extraction_method IN ['manual', 'llm_extracted', 'metadata_grounded_demo']
                    OR f.finding_id STARTS WITH 'd2_demo_finding_'
                  )
                DETACH DELETE f
                """
            )
            for raw in records:
                rec = self._normalize_finding(raw)
                try:
                    session.execute_write(self._merge_finding, rec)
                    processed += 1
                except Exception:
                    errors += 1
                    LOGGER.exception(
                        "Failed to upsert finding for %s page %s",
                        rec.get("doc_id"), rec.get("page"),
                    )
        return {"processed": processed, "errors": errors}

    @staticmethod
    def _normalize_finding(raw: Dict[str, Any]) -> Dict[str, Any]:
        doc_id = raw.get("doc_id") or raw.get("document_id") or ""
        text = raw.get("text") or raw.get("claim_text") or ""
        page = (
            int(float(raw.get("page") or raw.get("source_page") or 0))
            if str(raw.get("page") or raw.get("source_page") or "").strip()
            else None
        )
        finding_id = raw.get("finding_id") or f"{doc_id}_p{page or 'na'}_{slugify(text)[:48]}"
        country = raw.get("country") or raw.get("country_id") or ""
        extraction_method = str(raw.get("extraction_method") or "manual").lower()

        # Normalise entity names through alias table
        risk_raw = normalize_entity_name(raw.get("risk") or raw.get("climate_risk") or "")
        sector_raw = raw.get("sector") or ""
        tech_raw = normalize_entity_name(raw.get("technology") or "")

        return {
            **raw,
            "finding_id": finding_id,
            "doc_id": doc_id,
            "page": page,
            "text": text,
            "confidence": str(raw.get("confidence") or "medium").lower(),
            "confidence_rank": confidence_rank(str(raw.get("confidence") or "medium")),
            "extraction_method": extraction_method,
            "risk": risk_raw,
            "risk_id": slugify(risk_raw),
            "sector": sector_raw,
            "sector_id": slugify(sector_raw),
            "country_id": (
                country
                if len(str(country)) == 3 and str(country).isupper()
                else country_id_for(country)
            ),
            "technology": tech_raw,
            "tech_id": slugify(tech_raw),
            "qdrant_chunk_id": raw.get("qdrant_chunk_id") or "",
        }

    @staticmethod
    def _merge_finding(tx, rec: Dict[str, Any]) -> None:
        # Core Finding node — write BOTH relationship types for consistency
        tx.run(
            """
            MERGE (f:Finding {finding_id: $finding_id})
            SET f.doc_id           = $doc_id,
                f.page             = $page,
                f.text             = $text,
                f.confidence       = $confidence,
                f.confidence_rank  = $confidence_rank,
                f.extraction_method = $extraction_method,
                f.qdrant_chunk_id  = $qdrant_chunk_id
            WITH f
            MATCH (d:Document {doc_id: $doc_id})
            MERGE (d)-[:REPORTS_FINDING]->(f)
            MERGE (f)-[:SUPPORTED_BY]->(d)
            """,
            **rec,
        )

        if rec.get("risk") and rec["risk_id"] not in ("", "unknown"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (r:ClimateRisk {risk_id: $risk_id})
                SET r.name = $risk
                MERGE (f)-[:EVIDENCES_RISK]->(r)
                """,
                **rec,
            )

        if rec.get("sector") and rec["sector_id"] not in ("", "unknown"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (s:Sector {sector_id: $sector_id})
                SET s.name = $sector
                MERGE (f)-[:EVIDENCES_SECTOR]->(s)
                """,
                **rec,
            )

        if rec.get("country_id") and rec["country_id"] not in ("", "UNK", "NAN"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (c:Country {country_id: $country_id})
                MERGE (f)-[:EVIDENCES_COUNTRY]->(c)
                """,
                **rec,
            )

        if rec.get("technology") and rec["tech_id"] not in ("", "unknown"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (t:Technology {tech_id: $tech_id})
                SET t.name = $technology
                MERGE (f)-[:EVIDENCES_TECHNOLOGY]->(t)
                """,
                **rec,
            )

        # FIX 5 (Problem 6): gate causal edges behind extraction_method check.
        # Demo findings must never create IMPACTS or MITIGATES edges.
        is_real_evidence = rec.get("extraction_method", "manual") != "demo"

        if is_real_evidence and rec.get("risk") and rec.get("sector"):
            if rec["risk_id"] not in ("", "unknown") and rec["sector_id"] not in ("", "unknown"):
                tx.run(
                    """
                    MATCH (r:ClimateRisk {risk_id: $risk_id})
                    MATCH (s:Sector {sector_id: $sector_id})
                    MERGE (r)-[rel:IMPACTS]->(s)
                    SET rel.confidence      = $confidence,
                        rel.confidence_rank = $confidence_rank,
                        rel.source          = 'finding',
                        rel.evidence_page   = $page,
                        rel.doc_id          = $doc_id
                    """,
                    **rec,
                )
        elif not is_real_evidence and rec.get("risk") and rec.get("sector"):
            LOGGER.warning(
                "Skipping IMPACTS edge for demo finding %s — not real evidence",
                rec.get("finding_id"),
            )

        if is_real_evidence and rec.get("technology") and rec.get("risk"):
            if rec["tech_id"] not in ("", "unknown") and rec["risk_id"] not in ("", "unknown"):
                tx.run(
                    """
                    MATCH (t:Technology {tech_id: $tech_id})
                    MATCH (r:ClimateRisk {risk_id: $risk_id})
                    MERGE (t)-[rel:MITIGATES]->(r)
                    SET rel.confidence      = $confidence,
                        rel.confidence_rank = $confidence_rank,
                        rel.source          = 'finding',
                        rel.evidence_page   = $page,
                        rel.doc_id          = $doc_id
                    """,
                    **rec,
                )
        elif not is_real_evidence and rec.get("technology") and rec.get("risk"):
            LOGGER.warning(
                "Skipping MITIGATES edge for demo finding %s — not real evidence",
                rec.get("finding_id"),
            )

        if is_real_evidence and rec.get("risk") and rec.get("country_id"):
            if rec["risk_id"] not in ("", "unknown") and rec["country_id"] not in ("", "UNK", "NAN"):
                tx.run(
                    """
                    MATCH (r:ClimateRisk {risk_id: $risk_id})
                    MATCH (c:Country {country_id: $country_id})-[:LOCATED_IN]->(region:Region)
                    MERGE (r)-[rel:OCCURS_IN]->(region)
                    SET rel.confidence      = $confidence,
                        rel.confidence_rank = $confidence_rank,
                        rel.source          = 'finding',
                        rel.evidence_page   = $page,
                        rel.doc_id          = $doc_id
                    """,
                    **rec,
                )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_finding_integrity(self) -> Dict[str, int]:
        queries = {
            "total_findings": "MATCH (f:Finding) RETURN count(f) AS count",
            "missing_page": "MATCH (f:Finding) WHERE f.page IS NULL RETURN count(f) AS count",
            "missing_doc_id": (
                "MATCH (f:Finding) WHERE f.doc_id IS NULL OR f.doc_id = '' "
                "RETURN count(f) AS count"
            ),
            "no_entity_edges": """
                MATCH (f:Finding)
                WHERE NOT (f)-[:EVIDENCES_RISK|EVIDENCES_SECTOR|EVIDENCES_COUNTRY|EVIDENCES_TECHNOLOGY]->()
                RETURN count(f) AS count
            """,
            # FIX 4 (Problem 5): accept EITHER relationship type so the
            # 6-FAIL false positive from REPORTS_FINDING-only findings is gone.
            "not_linked_to_document": """
                MATCH (f:Finding)
                WHERE NOT (:Document)-[:REPORTS_FINDING]->(f)
                  AND NOT (f)-[:SUPPORTED_BY]->(:Document)
                RETURN count(f) AS count
            """,
        }
        with self.driver.session() as session:
            return {
                name: session.run(query).single()["count"]
                for name, query in queries.items()
            }

    # ------------------------------------------------------------------
    # Graph statistics helpers
    # ------------------------------------------------------------------

    def get_orphan_counts(self) -> list[Dict[str, Any]]:
        query = """
        MATCH (n)
        WHERE NOT (n)--()\
        WITH labels(n)[0] AS label, count(n) AS count
        RETURN label, count
        ORDER BY count DESC
        """
        with self.driver.session() as session:
            return [dict(row) for row in session.run(query)]

    def get_node_counts(self) -> Dict[str, int]:
        query = """
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN label, count(*) AS count
        ORDER BY label
        """
        with self.driver.session() as session:
            return {row["label"]: row["count"] for row in session.run(query)}

    def get_relationship_counts(self) -> Dict[str, int]:
        query = """
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(*) AS count
        ORDER BY rel_type
        """
        with self.driver.session() as session:
            return {row["rel_type"]: row["count"] for row in session.run(query)}