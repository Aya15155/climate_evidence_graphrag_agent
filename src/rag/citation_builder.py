# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: make GraphRAG return both graph facts and retrieved text chunks, then verify citations.
# - Improvement: add fallback behavior when Neo4j returns no climate concepts.
# ------------------------------------------------------------
def citation_for_chunk(chunk: dict) -> str:
    title = chunk.get("title") or chunk.get("document_id") or "Unknown source"
    page = chunk.get("start_page", "?")
    return f"[{title}, p.{page}]"
