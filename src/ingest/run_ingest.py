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
    metadata_path = Path("data/metadata/papers_metadata.csv")

    records = load_metadata(metadata_path)
    print(f"Loaded {len(records)} metadata rows")

    total_pdfs = 0
    total_pages = 0
    total_chunks = 0
    missing_pdfs = []

    for rec in records:
        pdf_path = Path(rec["pdf_path"])

        if not pdf_path.exists():
            print(f"[SKIP] Missing PDF: {pdf_path}")
            missing_pdfs.append(str(pdf_path))
            continue

        try:
            pages = load_pdf_pages(pdf_path, rec["document_id"])
            chunks = chunk_pages(pages)
        except Exception as exc:
            print(f"[ERROR] {rec['document_id']}: {exc}")
            continue

        total_pdfs += 1
        total_pages += len(pages)
        total_chunks += len(chunks)

        print(f"{rec['document_id']}: {len(pages)} pages, {len(chunks)} chunks")

    print("--------------------------------------------------")
    print(f"PDFs processed: {total_pdfs}")
    print(f"Total pages extracted: {total_pages}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Missing PDFs: {len(missing_pdfs)}")
    print("--------------------------------------------------")

    if missing_pdfs:
        print("Missing PDF files:")
        for pdf in missing_pdfs:
            print(f"- {pdf}")

    print("Next step: add this evidence to Reem's D2 notebook.")


if __name__ == "__main__":
    main()