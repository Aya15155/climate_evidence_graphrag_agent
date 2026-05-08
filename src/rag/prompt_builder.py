# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: make GraphRAG return both graph facts and retrieved text chunks, then verify citations.
# - Improvement: add fallback behavior when Neo4j returns no climate concepts.
# ------------------------------------------------------------
SYSTEM_PROMPT = """You are a climate evidence research assistant.
Answer ONLY using the provided context chunks and graph facts.
For every factual climate claim, cite the source using [Document Title, p.X].
If the evidence is not present, say: I could not find enough support in the uploaded climate documents.
Do not invent climate statistics, policy commitments, organizations, or page numbers.
"""


def build_prompt(question: str, chunks: list[dict], graph_facts: list[dict]) -> str:
    context = "\n\n".join(
        f"[{c.get('title', c.get('document_id'))}, p.{c.get('start_page')}] {c.get('text')}"
        for c in chunks
    )
    return f"{SYSTEM_PROMPT}\n\nGraph facts:\n{graph_facts}\n\nContext:\n{context}\n\nQuestion: {question}\nAnswer:"
