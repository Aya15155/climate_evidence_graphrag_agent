# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: keep this graph climate-specific; do not reduce it to only Paper/Author/Topic.
# - Improvement: add more relationship extraction rules from metadata and validated PDF evidence.
# - Improvement: add MERGE constraints/indexes for Document, Country, Policy, ClimateRisk, Technology, and Finding.
# - Improvement: extract Finding nodes from curated evidence rows, not only metadata fields.
# ------------------------------------------------------------
from typing import Dict
from src.ingest.metadata_loader import split_list_field

class ClimateGraphBuilder:
    """Builds the Climate Evidence Knowledge Graph in Neo4j.

    Rana owns this file. It intentionally uses climate-specific nodes, not only Paper/Topic.
    """
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="climate123"):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def upsert_document_graph(self, rec: Dict) -> None:
        with self.driver.session() as session:
            session.execute_write(self._merge_document_graph, rec)

    @staticmethod
    def _merge_document_graph(tx, rec: Dict) -> None:
        tx.run("""
        MERGE (d:Document {document_id: $document_id})
        SET d.title=$title, d.year=$year, d.document_type=$document_type, d.pdf_path=$pdf_path
        MERGE (o:Organization {name: $organization})
        MERGE (d)-[:PUBLISHED_BY]->(o)
        MERGE (v:Venue {name: $venue})
        MERGE (d)-[:PUBLISHED_IN]->(v)
        """, **rec)

        for field, label, rel in [
            ("topics", "ClimateTopic", "DISCUSSES"),
            ("countries", "Country", "MENTIONS_COUNTRY"),
            ("regions", "Region", "MENTIONS_REGION"),
            ("sectors", "Sector", "AFFECTS_SECTOR"),
            ("climate_risks", "ClimateRisk", "DISCUSSES_RISK"),
            ("technologies", "Technology", "MENTIONS_TECHNOLOGY"),
            ("policies", "Policy", "DISCUSSES_POLICY"),
            ("targets", "Target", "DISCUSSES_TARGET"),
            ("indicators", "Indicator", "REPORTS_INDICATOR"),
        ]:
            for name in split_list_field(rec.get(field, "")):
                tx.run(f"""
                MATCH (d:Document {{document_id: $document_id}})
                MERGE (n:{label} {{name: $name}})
                MERGE (d)-[:{rel}]->(n)
                """, document_id=rec["document_id"], name=name)

        for country in split_list_field(rec.get("countries", "")):
            for policy in split_list_field(rec.get("policies", "")):
                tx.run("""
                MERGE (c:Country {name: $country})
                MERGE (p:Policy {name: $policy})
                MERGE (c)-[:HAS_POLICY]->(p)
                """, country=country, policy=policy)
            for region in split_list_field(rec.get("regions", "")):
                tx.run("""
                MERGE (c:Country {name: $country})
                MERGE (r:Region {name: $region})
                MERGE (c)-[:LOCATED_IN]->(r)
                """, country=country, region=region)

        for policy in split_list_field(rec.get("policies", "")):
            for target in split_list_field(rec.get("targets", "")):
                tx.run("""
                MERGE (p:Policy {name: $policy})
                MERGE (t:Target {name: $target})
                MERGE (p)-[:SETS_TARGET]->(t)
                """, policy=policy, target=target)
