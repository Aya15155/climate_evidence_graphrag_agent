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


COUNTRY_IDS = {
    "uae": "ARE",
    "united arab emirates": "ARE",
    "global": "GLOBAL",
    "saudi arabia": "SAU",
    "egypt": "EGY",
    "jordan": "JOR",
    "germany": "DEU",
}


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
            except Exception as exc:  # pragma: no cover - depends on local Neo4j
                last_error = exc
                time.sleep(retry_seconds)
        raise ConnectionError(
            f"Could not connect to Neo4j at {uri}. Start Neo4j with docker-compose up -d neo4j "
            "or check NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD."
        ) from last_error

    def close(self) -> None:
        self.driver.close()

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
            session.execute_write(self._merge_document_graph, self._normalize_document(rec), True)

    @staticmethod
    def _normalize_document(raw: Dict[str, Any]) -> Dict[str, Any]:
        title = raw.get("title") or "Untitled climate document"
        doc_id = raw.get("doc_id") or raw.get("document_id") or slugify(title)
        return {
            **raw,
            "doc_id": str(doc_id),
            "title": title,
            "year": int(float(raw.get("year") or 0)) if str(raw.get("year") or "").strip() else None,
            "doc_type": raw.get("doc_type") or raw.get("document_type") or "",
            "organization": raw.get("organization") or "Unknown Organization",
            "org_id": slugify(raw.get("organization") or "Unknown Organization"),
            "venue": raw.get("venue") or "Unknown Venue",
            "venue_id": slugify(raw.get("venue") or "Unknown Venue"),
            "language": raw.get("language") or "en",
            "url": raw.get("url") or raw.get("pdf_path") or "",
            "page_count": int(float(raw.get("page_count") or raw.get("total_pages") or 0))
            if str(raw.get("page_count") or raw.get("total_pages") or "").strip()
            else None,
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
        ClimateGraphBuilder._merge_list_entities(tx, rec, "regions", "Region", "region_id", "MENTIONS_REGION")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "sectors", "Sector", "sector_id", "AFFECTS_SECTOR")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "climate_risks", "ClimateRisk", "risk_id", "DISCUSSES_RISK")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "technologies", "Technology", "tech_id", "MENTIONS_TECHNOLOGY")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "policies", "Policy", "policy_id", "DISCUSSES_POLICY")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "targets", "Target", "target_id", "DISCUSSES_TARGET")
        ClimateGraphBuilder._merge_list_entities(tx, rec, "indicators", "Indicator", "indicator_id", "REPORTS_INDICATOR")
        ClimateGraphBuilder._merge_metadata_relationships(tx, rec)

    @staticmethod
    def _merge_list_entities(
        tx, rec: Dict[str, Any], field: str, label: str, id_prop: str, document_rel: str
    ) -> None:
        for name in split_list_field(rec.get(field, "")):
            entity_id = slugify(name)
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
        for name in split_list_field(rec.get("countries", "")):
            cid = country_id_for(name)
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

    @staticmethod
    def _merge_metadata_relationships(tx, rec: Dict[str, Any]) -> None:
        for country in split_list_field(rec.get("countries", "")):
            cid = country_id_for(country)
            for region in split_list_field(rec.get("regions", "")):
                tx.run(
                    """
                    MERGE (c:Country {country_id: $country_id})
                    SET c.name = $country
                    MERGE (r:Region {region_id: $region_id})
                    SET r.name = $region
                    MERGE (c)-[:LOCATED_IN]->(r)
                    """,
                    country_id=cid,
                    country=country,
                    region_id=slugify(region),
                    region=region,
                )
            for policy in split_list_field(rec.get("policies", "")):
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
                    policy_id=slugify(policy),
                    policy=policy,
                )

        for policy in split_list_field(rec.get("policies", "")):
            for target in split_list_field(rec.get("targets", "")):
                tx.run(
                    """
                    MERGE (p:Policy {policy_id: $policy_id})
                    SET p.name = $policy
                    MERGE (t:Target {target_id: $target_id})
                    SET t.name = $target
                    MERGE (p)-[:SETS_TARGET]->(t)
                    """,
                    policy_id=slugify(policy),
                    policy=policy,
                    target_id=slugify(target),
                    target=target,
                )
            for topic in split_list_field(rec.get("topics", "")):
                tx.run(
                    """
                    MERGE (p:Policy {policy_id: $policy_id})
                    SET p.name = $policy
                    MERGE (t:ClimateTopic {topic_id: $topic_id})
                    SET t.name = $topic
                    MERGE (p)-[:ADDRESSES]->(t)
                    """,
                    policy_id=slugify(policy),
                    policy=policy,
                    topic_id=slugify(topic),
                    topic=topic,
                )

        for topic in split_list_field(rec.get("topics", "")):
            for risk in split_list_field(rec.get("climate_risks", "")):
                tx.run(
                    """
                    MERGE (t:ClimateTopic {topic_id: $topic_id})
                    SET t.name = $topic
                    MERGE (r:ClimateRisk {risk_id: $risk_id})
                    SET r.name = $risk
                    MERGE (t)-[:HAS_RISK]->(r)
                    """,
                    topic_id=slugify(topic),
                    topic=topic,
                    risk_id=slugify(risk),
                    risk=risk,
                )

    def bulk_upsert_findings(self, records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        processed = 0
        errors = 0
        with self.driver.session() as session:
            for raw in records:
                rec = self._normalize_finding(raw)
                try:
                    session.execute_write(self._merge_finding, rec)
                    processed += 1
                except Exception:
                    errors += 1
                    LOGGER.exception("Failed to upsert finding for %s page %s", rec.get("doc_id"), rec.get("page"))
        return {"processed": processed, "errors": errors}

    @staticmethod
    def _normalize_finding(raw: Dict[str, Any]) -> Dict[str, Any]:
        doc_id = raw.get("doc_id") or raw.get("document_id") or ""
        text = raw.get("text") or raw.get("claim_text") or ""
        page = int(float(raw.get("page") or raw.get("source_page") or 0)) if str(raw.get("page") or raw.get("source_page") or "").strip() else None
        finding_id = raw.get("finding_id") or f"{doc_id}_p{page or 'na'}_{slugify(text)[:48]}"
        country = raw.get("country") or raw.get("country_id") or ""
        return {
            **raw,
            "finding_id": finding_id,
            "doc_id": doc_id,
            "page": page,
            "text": text,
            "confidence": str(raw.get("confidence") or "medium").lower(),
            "confidence_rank": confidence_rank(str(raw.get("confidence") or "medium")),
            "extraction_method": raw.get("extraction_method") or "manual",
            "risk": raw.get("risk") or raw.get("climate_risk") or "",
            "risk_id": slugify(raw.get("risk") or raw.get("climate_risk") or ""),
            "sector": raw.get("sector") or "",
            "sector_id": slugify(raw.get("sector") or ""),
            "country_id": country if len(str(country)) == 3 and str(country).isupper() else country_id_for(country),
            "technology": raw.get("technology") or "",
            "tech_id": slugify(raw.get("technology") or ""),
            "qdrant_chunk_id": raw.get("qdrant_chunk_id") or "",
        }

    @staticmethod
    def _merge_finding(tx, rec: Dict[str, Any]) -> None:
        tx.run(
            """
            MERGE (f:Finding {finding_id: $finding_id})
            SET f.doc_id = $doc_id,
                f.page = $page,
                f.text = $text,
                f.confidence = $confidence,
                f.confidence_rank = $confidence_rank,
                f.extraction_method = $extraction_method,
                f.qdrant_chunk_id = $qdrant_chunk_id
            WITH f
            MATCH (d:Document {doc_id: $doc_id})
            MERGE (d)-[:REPORTS_FINDING]->(f)
            MERGE (f)-[:SUPPORTED_BY]->(d)
            """,
            **rec,
        )
        if rec.get("risk"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (r:ClimateRisk {risk_id: $risk_id})
                SET r.name = $risk
                MERGE (f)-[:EVIDENCES_RISK]->(r)
                """,
                **rec,
            )
        if rec.get("sector"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (s:Sector {sector_id: $sector_id})
                SET s.name = $sector
                MERGE (f)-[:EVIDENCES_SECTOR]->(s)
                """,
                **rec,
            )
        if rec.get("country_id"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (c:Country {country_id: $country_id})
                MERGE (f)-[:EVIDENCES_COUNTRY]->(c)
                """,
                **rec,
            )
        if rec.get("technology"):
            tx.run(
                """
                MATCH (f:Finding {finding_id: $finding_id})
                MERGE (t:Technology {tech_id: $tech_id})
                SET t.name = $technology
                MERGE (f)-[:EVIDENCES_TECHNOLOGY]->(t)
                """,
                **rec,
            )
        if rec.get("risk") and rec.get("sector"):
            tx.run(
                """
                MATCH (r:ClimateRisk {risk_id: $risk_id})
                MATCH (s:Sector {sector_id: $sector_id})
                MERGE (r)-[rel:IMPACTS]->(s)
                SET rel.confidence = $confidence,
                    rel.confidence_rank = $confidence_rank,
                    rel.source = 'finding',
                    rel.evidence_page = $page,
                    rel.doc_id = $doc_id
                """,
                **rec,
            )
        if rec.get("technology") and rec.get("risk"):
            tx.run(
                """
                MATCH (t:Technology {tech_id: $tech_id})
                MATCH (r:ClimateRisk {risk_id: $risk_id})
                MERGE (t)-[rel:MITIGATES]->(r)
                SET rel.confidence = $confidence,
                    rel.confidence_rank = $confidence_rank,
                    rel.source = 'finding',
                    rel.evidence_page = $page,
                    rel.doc_id = $doc_id
                """,
                **rec,
            )
        if rec.get("risk") and rec.get("country_id"):
            tx.run(
                """
                MATCH (r:ClimateRisk {risk_id: $risk_id})
                MATCH (c:Country {country_id: $country_id})-[:LOCATED_IN]->(region:Region)
                MERGE (r)-[rel:OCCURS_IN]->(region)
                SET rel.confidence = $confidence,
                    rel.confidence_rank = $confidence_rank,
                    rel.source = 'finding',
                    rel.evidence_page = $page,
                    rel.doc_id = $doc_id
                """,
                **rec,
            )

    def validate_finding_integrity(self) -> Dict[str, int]:
        queries = {
            "total_findings": "MATCH (f:Finding) RETURN count(f) AS count",
            "missing_page": "MATCH (f:Finding) WHERE f.page IS NULL RETURN count(f) AS count",
            "missing_doc_id": "MATCH (f:Finding) WHERE f.doc_id IS NULL OR f.doc_id = '' RETURN count(f) AS count",
            "no_entity_edges": """
                MATCH (f:Finding)
                WHERE NOT (f)-[:EVIDENCES_RISK|EVIDENCES_SECTOR|EVIDENCES_COUNTRY|EVIDENCES_TECHNOLOGY]->()
                RETURN count(f) AS count
            """,
            "not_linked_to_document": """
                MATCH (f:Finding)
                WHERE NOT (f)-[:SUPPORTED_BY]->(:Document)
                RETURN count(f) AS count
            """,
        }
        with self.driver.session() as session:
            return {name: session.run(query).single()["count"] for name, query in queries.items()}

    def get_orphan_counts(self) -> list[Dict[str, Any]]:
        query = """
        MATCH (n)
        WHERE NOT (n)--()
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
