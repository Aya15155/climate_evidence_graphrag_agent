# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from pathlib import Path
from .metadata_loader import load_metadata
from .pdf_loader import load_pdf_pages
from .chunker import chunk_pages


def main() -> None:
    metadata_path = Path("data/metadata/papers_metadata_template.csv")
    records = load_metadata(metadata_path)
    print(f"Loaded {len(records)} metadata rows")
    for rec in records:
        pdf_path = Path(rec["pdf_path"])
        if not pdf_path.exists():
            print(f"[SKIP] Missing PDF: {pdf_path}")
            continue
        pages = load_pdf_pages(pdf_path, rec["document_id"])
        chunks = chunk_pages(pages)
        print(f"{rec['document_id']}: {len(pages)} pages, {len(chunks)} chunks")
    print("Next step: connect MongoDB, Qdrant, and Neo4j once PDFs are available.")

if __name__ == "__main__":
    main()
