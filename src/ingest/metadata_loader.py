# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from pathlib import Path
from typing import Dict, List
import pandas as pd

# Columns that must exist in the CSV for the pipeline to work.
CLIMATE_METADATA_FIELDS = [
    "document_id", "title", "authors", "organization", "venue", "year", "document_type",
    "pdf_path", "topics", "countries", "regions", "sectors", "climate_risks",
    "technologies", "policies", "targets", "indicators", "total_pages",
]

# Columns that are useful but not required — tolerated if missing.
OPTIONAL_FIELDS = ["doi", "doi_or_url", "license", "abstract",
                   "doc_number", "pdf_url", "source_api", "external_id"]


def load_metadata(csv_path: str | Path) -> List[Dict]:
    # utf-8-sig handles the BOM character that Excel/Google Sheets sometimes adds
    df = pd.read_csv(csv_path, encoding="utf-8-sig").fillna("")
    missing = [c for c in CLIMATE_METADATA_FIELDS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing climate metadata columns: {missing}")
    # Alias doi_or_url -> doi so downstream code can always use rec["doi"]
    if "doi" not in df.columns and "doi_or_url" in df.columns:
        df["doi"] = df["doi_or_url"]
    if "license" not in df.columns:
        df["license"] = ""
    return df.to_dict(orient="records")


def split_list_field(value: str) -> list[str]:
    return [x.strip() for x in str(value).replace(",", ";").split(";") if x.strip()]
