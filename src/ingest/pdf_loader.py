# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class PageText:
    document_id: str
    page_number: int
    text: str


def load_pdf_pages(pdf_path: str | Path, document_id: str) -> List[PageText]:
    """Extract page-level text from one PDF.

    Reem owns this file. Each page must keep its page number so Alia/Rana can later
    verify citations and GraphRAG page ranges.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("Install pdfplumber to parse PDFs: pip install pdfplumber") from exc

    pages: List[PageText] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(document_id=document_id, page_number=i, text=text))
    return pages
