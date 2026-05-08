# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
def verify_page_range(chunk: dict) -> bool:
    """Check that a chunk has valid citation metadata.

    Reem owns this file for D3. Later, extend it to reopen the PDF and verify the
    cited text actually appears on the cited page.
    """
    return bool(chunk.get("document_id")) and int(chunk.get("start_page", 0)) > 0 and int(chunk.get("end_page", 0)) >= int(chunk.get("start_page", 0))
