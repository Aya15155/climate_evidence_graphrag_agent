# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from pathlib import Path
from typing import Dict, List
import pandas as pd

CLIMATE_METADATA_FIELDS = [
    "document_id", "title", "authors", "organization", "venue", "year", "document_type",
    "pdf_path", "topics", "countries", "regions", "sectors", "climate_risks",
    "technologies", "policies", "targets", "indicators", "doi", "license", "total_pages",
]


def load_metadata(csv_path: str | Path) -> List[Dict]:
    df = pd.read_csv(csv_path).fillna("")
    missing = [c for c in CLIMATE_METADATA_FIELDS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing climate metadata columns: {missing}")
    return df.to_dict(orient="records")


def split_list_field(value: str) -> list[str]:
    return [x.strip() for x in str(value).replace(",", ";").split(";") if x.strip()]
