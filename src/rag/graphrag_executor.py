# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: make GraphRAG return both graph facts and retrieved text chunks, then verify citations.
# - Improvement: add fallback behavior when Neo4j returns no climate concepts.
# - Improvement: route query entities to exact Cypher query functions, then use resulting document IDs as retrieval filters.
# - Improvement: include graph paths in the final answer trace so the demo proves real graph reasoning.
# ------------------------------------------------------------
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class GraphRAGResult:
    answer: str
    citations: List[str]
    retrieved_chunks: List[Dict]
    graph_context: List[Dict]


CLIMATE_KEYWORDS = {
    "countries": ["UAE", "United Arab Emirates", "Germany", "France", "Saudi Arabia"],
    "risks": ["sea level rise", "heatwaves", "flooding", "water scarcity", "drought"],
    "sectors": ["energy", "transport", "agriculture", "buildings", "industry"],
    "technologies": ["green hydrogen", "solar", "carbon capture", "renewable energy", "transformer"],
    "topics": ["mitigation", "adaptation", "climate science", "policy", "emissions"],
}


def extract_climate_entities(query: str) -> Dict[str, List[str]]:
    q = query.lower()
    found = {k: [] for k in CLIMATE_KEYWORDS}
    for group, values in CLIMATE_KEYWORDS.items():
        for value in values:
            if value.lower() in q:
                found[group].append(value)
    return found


class ClimateGraphRAGExecutor:
    """Climate-specific GraphRAG pipeline.

    Rana owns this file. It should not only retrieve PDFs; it should use climate entities
    to find policies, risks, sectors, technologies, and evidence documents.
    """
    def __init__(self, hybrid_retriever=None, graph_client=None, answer_generator=None, citation_verifier=None):
        self.hybrid_retriever = hybrid_retriever
        self.graph_client = graph_client
        self.answer_generator = answer_generator
        self.citation_verifier = citation_verifier

    def ask(self, question: str, k: int = 5) -> GraphRAGResult:
        entities = extract_climate_entities(question)
        graph_context = self._query_graph(entities)
        filters = self._filters_from_graph_context(graph_context)
        chunks = self.hybrid_retriever.search(question, k=k, filters=filters) if self.hybrid_retriever else []
        answer = self._generate_answer(question, chunks, graph_context)
        citations = [c.get("citation", f"{c.get('title', c.get('document_id', 'source'))}, p.{c.get('start_page', '?')}") for c in chunks]
        if self.citation_verifier:
            answer = self.citation_verifier.verify(answer, chunks)["answer"]
        return GraphRAGResult(answer=answer, citations=citations, retrieved_chunks=chunks, graph_context=graph_context)

    def _query_graph(self, entities: Dict[str, List[str]]) -> List[Dict]:
        # TODO: call Neo4j using src.graph.cypher_queries.
        return [{"detected_entities": entities}]

    def _filters_from_graph_context(self, graph_context: List[Dict]) -> Dict:
        # TODO: convert graph results into Qdrant/Mongo filters.
        return {}

    def _generate_answer(self, question: str, chunks: List[Dict], graph_context: List[Dict]) -> str:
        if not chunks:
            return "I could not find enough supported evidence in the climate document set."
        evidence = "\n".join([f"[{c.get('title', c.get('document_id'))}, p.{c.get('start_page')}] {c.get('text', '')[:300]}" for c in chunks])
        return f"Draft answer for: {question}\n\nEvidence used:\n{evidence}\n\nReplace this with the final LLM-generated citation-grounded answer."
