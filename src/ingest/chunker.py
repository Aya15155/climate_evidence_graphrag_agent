# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from dataclasses import dataclass
from typing import Iterable, List
from .pdf_loader import PageText

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    start_page: int
    end_page: int


def chunk_pages(pages: Iterable[PageText], chunk_size: int = 600, overlap: int = 80) -> List[Chunk]:
    """Simple page-aware chunking. Keeps page ranges for citations."""
    chunks: List[Chunk] = []
    for page in pages:
        text = " ".join(page.text.split())
        if not text:
            continue
        start = 0
        idx = 0
        step = max(1, chunk_size - overlap)
        while start < len(text):
            part = text[start:start + chunk_size]
            chunks.append(Chunk(
                chunk_id=f"{page.document_id}_p{page.page_number}_c{idx}",
                document_id=page.document_id,
                text=part,
                start_page=page.page_number,
                end_page=page.page_number,
            ))
            start += step
            idx += 1
    return chunks
