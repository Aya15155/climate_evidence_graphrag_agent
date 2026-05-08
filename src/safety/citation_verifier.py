# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: test fake climate statistics, fake COP commitments, and prompt-injection attempts.
# - Improvement: refuse unsupported answers when retrieved chunks do not contain enough evidence.
# - Improvement: verify cited title + page number against retrieved chunks and optionally reopen the PDF page for confirmation.
# ------------------------------------------------------------
import re

CITATION_PATTERN = re.compile(r"\[(?P<title>[^\]]+),\s*p\.?\s*(?P<page>\d+|\?)\]")


def extract_citations(answer: str) -> list[dict]:
    return [m.groupdict() for m in CITATION_PATTERN.finditer(answer)]


class CitationVerifier:
    """Alia owns this file. It detects hallucinated citations."""
    def verify(self, answer: str, retrieved_chunks: list[dict]) -> dict:
        retrieved_titles = {c.get("title") or c.get("document_id") for c in retrieved_chunks}
        bad = []
        for cit in extract_citations(answer):
            title = cit["title"]
            if title not in retrieved_titles:
                bad.append(title)
        if bad:
            answer += f"\n\nWARNING: Unverified citations detected: {bad}"
        return {"answer": answer, "unverified_citations": bad}
