from __future__ import annotations

from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import pandas as pd
import pdfplumber
import requests
from tqdm import tqdm


# =========================================================
# Climate Evidence GraphRAG Agent — Full Dataset Builder
# =========================================================
# D1 target:
# - exactly 300 successfully processed PDFs
# - no max chunks limit
# - metadata CSV
# - sample_chunks.json
# - 300 draft retrieval Q/A items for Salma
#
# Sources:
# - arXiv
# - OpenAlex
# - Europe PMC
#
# Important:
# Automatically generated Q/A is a DRAFT. It must be reviewed.
# =========================================================


ARXIV_API_URL = "http://export.arxiv.org/api/query"
OPENALEX_API_URL = "https://api.openalex.org/works"
EUROPE_PMC_API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

HEADERS = {
    "User-Agent": "ClimateEvidenceGraphRAGAgent/1.0 student project open-access PDF collection"
}


SEARCH_QUERIES = [
    "climate change machine learning",
    "climate change artificial intelligence",
    "climate change deep learning",
    "climate forecasting machine learning",
    "climate downscaling deep learning",
    "climate prediction neural networks",
    "remote sensing climate change",
    "earth observation climate change",
    "renewable energy forecasting machine learning",
    "solar energy forecasting",
    "wind energy forecasting",
    "carbon emissions machine learning",
    "greenhouse gas emissions prediction",
    "climate risk assessment machine learning",
    "climate vulnerability assessment",
    "sustainability artificial intelligence",
    "climate policy analysis",
    "climate adaptation resilience",
    "climate finance adaptation",
    "water scarcity climate change",
    "food security climate change",
    "sea level rise infrastructure",
    "green hydrogen climate mitigation",
    "carbon capture climate mitigation",
    "net zero transition energy",
    "energy transition climate policy",
    "climate change public health",
    "climate change agriculture",
    "climate change water resources",
    "urban climate resilience",
    "climate change mitigation pathways",
    "low carbon technology",
    "sustainable development goals climate",
    "climate change Middle East",
    "climate change Gulf region",
    "climate policy governance",
    "adaptation gap climate",
    "emissions gap climate",
]


COUNTRY_KEYWORDS = {
    "UAE": ["uae", "united arab emirates", "emirates", "abu dhabi", "dubai"],
    "Oman": ["oman"],
    "Saudi Arabia": ["saudi arabia", "ksa", "kingdom of saudi arabia"],
    "Qatar": ["qatar"],
    "Kuwait": ["kuwait"],
    "Bahrain": ["bahrain"],
    "Egypt": ["egypt"],
    "Germany": ["germany"],
    "United States": ["united states", "usa", "u.s."],
    "China": ["china"],
    "India": ["india"],
    "Global": ["global", "worldwide", "international"],
}

REGION_KEYWORDS = {
    "Middle East": ["middle east", "mena", "gulf", "gcc", "arabian peninsula"],
    "Gulf Region": ["gulf", "gcc", "arabian gulf"],
    "Global South": ["global south", "developing countries"],
    "Europe": ["europe", "european union", "eu"],
    "Asia": ["asia", "asian"],
    "Africa": ["africa", "african"],
    "Global": ["global", "worldwide", "international"],
}

TOPIC_KEYWORDS = {
    "climate science": ["climate science", "warming", "temperature", "greenhouse gas", "climate system"],
    "mitigation": ["mitigation", "emission reduction", "emissions reduction", "decarbonization", "decarbonisation"],
    "adaptation": ["adaptation", "resilience", "adaptive capacity"],
    "policy and governance": ["policy", "governance", "agreement", "pledge", "consensus", "commitment"],
    "renewable energy": ["renewable energy", "renewables", "solar", "wind", "clean energy"],
    "energy transition": ["energy transition", "net zero", "phase-out", "phase down", "fossil fuels"],
    "climate finance": ["climate finance", "adaptation finance", "loss and damage", "investment"],
    "climate AI": ["machine learning", "artificial intelligence", "deep learning", "neural network", "transformer"],
    "carbon capture": ["carbon capture", "ccus", "carbon storage", "carbon removal"],
    "sea level rise": ["sea level rise", "coastal flooding", "coastal risk"],
    "sustainability": ["sustainability", "sustainable development", "sdg", "sdgs"],
}

SECTOR_KEYWORDS = {
    "energy": ["energy", "power", "electricity", "renewable"],
    "transport": ["transport", "transportation", "mobility", "vehicles"],
    "agriculture": ["agriculture", "crop", "food security", "irrigation", "farming"],
    "buildings": ["buildings", "construction", "built environment"],
    "industry": ["industry", "industrial", "manufacturing", "steel", "cement"],
    "water": ["water", "water scarcity", "desalination"],
    "infrastructure": ["infrastructure", "coastal infrastructure", "urban infrastructure"],
    "health": ["health", "public health", "heat stress"],
    "finance": ["finance", "investment", "green finance"],
}

RISK_KEYWORDS = {
    "heatwaves": ["heatwave", "heatwaves", "extreme heat", "heat stress"],
    "drought": ["drought", "dryness", "aridity"],
    "water scarcity": ["water scarcity", "water stress", "water shortage"],
    "sea level rise": ["sea level rise", "coastal flooding", "storm surge"],
    "flooding": ["flood", "flooding", "flash flood"],
    "food insecurity": ["food insecurity", "food security", "crop failure"],
    "emissions": ["emissions", "greenhouse gas", "co2", "carbon dioxide"],
    "climate vulnerability": ["vulnerability", "climate vulnerability"],
}

TECHNOLOGY_KEYWORDS = {
    "green hydrogen": ["green hydrogen", "hydrogen"],
    "solar PV": ["solar pv", "solar photovoltaic", "solar energy"],
    "wind energy": ["wind energy", "wind power"],
    "carbon capture": ["carbon capture", "ccus", "carbon storage"],
    "battery storage": ["battery storage", "energy storage", "batteries"],
    "electric vehicles": ["electric vehicles", "evs", "e-mobility"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "neural network"],
    "transformer": ["transformer", "attention model"],
    "climate downscaling": ["downscaling", "climate downscaling"],
    "remote sensing": ["remote sensing", "satellite imagery", "earth observation"],
    "forecasting": ["forecasting", "prediction", "predictive model"],
}

POLICY_KEYWORDS = {
    "UAE Net Zero 2050": ["uae net zero 2050", "net zero by 2050", "net zero 2050"],
    "COP28 UAE Consensus": ["uae consensus", "cop28", "global stocktake"],
    "Paris Agreement": ["paris agreement"],
    "Nationally Determined Contributions": ["nationally determined contribution", "ndc", "ndcs"],
    "Net Zero Strategy": ["net zero strategy", "net-zero strategy"],
    "National Climate Action Plan": ["national climate action plan", "climate action plan"],
}

TARGET_KEYWORDS = {
    "Net Zero by 2050": ["net zero by 2050", "net-zero by 2050", "net zero 2050"],
    "Triple Renewable Energy": ["triple renewable energy", "tripling renewable energy", "triple renewables"],
    "Double Energy Efficiency": ["double energy efficiency", "doubling energy efficiency"],
    "Reduce Emissions": ["reduce emissions", "emission reduction", "emissions reduction"],
    "Limit Warming to 1.5C": ["1.5°c", "1.5 c", "1.5 degrees", "limit warming"],
}

INDICATOR_KEYWORDS = {
    "CO2 emissions": ["co2 emissions", "carbon dioxide emissions", "greenhouse gas emissions"],
    "temperature rise": ["temperature rise", "warming", "global temperature"],
    "sea level": ["sea level", "sea-level"],
    "renewable capacity": ["renewable capacity", "installed capacity"],
    "energy efficiency": ["energy efficiency"],
    "climate finance": ["climate finance", "investment"],
    "water demand": ["water demand", "water consumption"],
}


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def slugify(text: str, max_len: int = 120) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len].strip("_") or "untitled"


def stable_hash(text: str, length: int = 8) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:length]


def make_doc_number(index: int) -> str:
    return f"D{index:03d}"


def get_first_author_lastname(authors: str) -> str:
    if not authors:
        return "unknown_author"
    first_author = authors.split(";")[0].strip()
    parts = re.split(r"\s+", first_author)
    return slugify(parts[-1] if parts else "unknown_author", max_len=30)


def short_title_slug(title: str, max_words: int = 8) -> str:
    stopwords = {
        "a", "an", "the", "and", "or", "of", "for", "to", "in", "on",
        "with", "using", "via", "by", "from", "towards", "toward",
        "based", "approach", "study", "analysis", "model", "models"
    }
    words = re.findall(r"[a-z0-9]+", title.lower())
    words = [w for w in words if w not in stopwords]
    return "_".join(words[:max_words]) if words else "untitled"


def make_document_id(paper: dict[str, Any]) -> str:
    author = get_first_author_lastname(paper.get("authors", ""))
    year = str(paper.get("year") or "unknown_year")
    title_slug = short_title_slug(paper.get("title", ""), max_words=8)
    source_id = slugify(str(paper.get("external_id") or stable_hash(paper.get("pdf_url", ""))), max_len=35)
    return slugify(f"{author}_{year}_{title_slug}_{source_id}", max_len=150)


def detect_keywords(text: str, keyword_dict: dict[str, list[str]]) -> list[str]:
    text_lower = text.lower()
    found = []
    for label, keywords in keyword_dict.items():
        if any(keyword.lower() in text_lower for keyword in keywords):
            found.append(label)
    return sorted(set(found))


def join_values(values: list[str]) -> str:
    return "; ".join(sorted(set(v for v in values if v)))


def infer_metadata_from_text(text: str) -> dict[str, list[str]]:
    return {
        "topics": detect_keywords(text, TOPIC_KEYWORDS),
        "countries": detect_keywords(text, COUNTRY_KEYWORDS),
        "regions": detect_keywords(text, REGION_KEYWORDS),
        "sectors": detect_keywords(text, SECTOR_KEYWORDS),
        "climate_risks": detect_keywords(text, RISK_KEYWORDS),
        "technologies": detect_keywords(text, TECHNOLOGY_KEYWORDS),
        "policies": detect_keywords(text, POLICY_KEYWORDS),
        "targets": detect_keywords(text, TARGET_KEYWORDS),
        "indicators": detect_keywords(text, INDICATOR_KEYWORDS),
    }


def is_climate_related(title: str, abstract: str) -> bool:
    combined = f"{title} {abstract}".lower()
    required_terms = [
        "climate", "carbon", "emission", "sustainability", "sustainable",
        "renewable", "solar", "wind", "energy", "net zero", "greenhouse",
        "adaptation", "mitigation", "sea level", "water scarcity"
    ]
    return any(term in combined for term in required_terms)


def unique_key_for_paper(paper: dict[str, Any]) -> str:
    title_key = slugify(paper.get("title", ""), max_len=100)
    year = str(paper.get("year") or "")
    doi_or_url = str(paper.get("doi_or_url") or "")
    return f"{title_key}_{year}_{stable_hash(doi_or_url)}"


def parse_arxiv_authors(author_nodes: list[ET.Element], ns: dict[str, str]) -> str:
    authors = []
    for author_node in author_nodes:
        name_node = author_node.find("atom:name", ns)
        if name_node is not None and name_node.text:
            authors.append(normalize_space(name_node.text))
    return "; ".join(authors)


def search_arxiv(query: str, per_query: int, start: int = 0) -> list[dict[str, Any]]:
    params = {
        "search_query": f'all:"{query}"',
        "start": start,
        "max_results": per_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = requests.get(ARXIV_API_URL, params=params, headers=HEADERS, timeout=60)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    papers = []
    for entry in root.findall("atom:entry", ns):
        id_node = entry.find("atom:id", ns)
        title_node = entry.find("atom:title", ns)
        summary_node = entry.find("atom:summary", ns)
        published_node = entry.find("atom:published", ns)

        arxiv_url = normalize_space(id_node.text if id_node is not None else "")
        arxiv_id = arxiv_url.rstrip("/").split("/")[-1]
        title = normalize_space(title_node.text if title_node is not None else "")
        abstract = normalize_space(summary_node.text if summary_node is not None else "")
        published = normalize_space(published_node.text if published_node is not None else "")
        year = published[:4] if published else ""
        authors = parse_arxiv_authors(entry.findall("atom:author", ns), ns)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        if not is_climate_related(title, abstract):
            continue

        papers.append({
            "source_api": "arXiv",
            "external_id": arxiv_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "organization": "arXiv",
            "venue": "arXiv",
            "year": year,
            "document_type": "Research Paper",
            "doi_or_url": arxiv_url,
            "pdf_url": pdf_url,
        })
    return papers


def get_openalex_authors(work: dict[str, Any]) -> str:
    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        name = author.get("display_name")
        if name:
            authors.append(name)
    return "; ".join(authors)


def search_openalex(query: str, per_query: int, page: int = 1, mailto: str | None = None) -> list[dict[str, Any]]:
    params = {
        "search": query,
        "filter": "open_access.is_oa:true,type:article",
        "per-page": min(per_query, 200),
        "page": page,
        "sort": "cited_by_count:desc",
    }
    if mailto:
        params["mailto"] = mailto

    response = requests.get(OPENALEX_API_URL, params=params, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()

    papers = []
    for work in data.get("results", []):
        title = normalize_space(work.get("title", ""))
        year = str(work.get("publication_year") or "")
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        venue = source.get("display_name") or "OpenAlex"

        pdf_url = primary_location.get("pdf_url")
        landing_url = primary_location.get("landing_page_url")
        if not pdf_url:
            open_access = work.get("open_access") or {}
            pdf_url = open_access.get("oa_url")

        if not pdf_url:
            continue

        authors = get_openalex_authors(work)
        doi = work.get("doi") or landing_url or work.get("id") or ""

        if not is_climate_related(title, ""):
            continue

        papers.append({
            "source_api": "OpenAlex",
            "external_id": str(work.get("id", "")).rstrip("/").split("/")[-1],
            "title": title,
            "abstract": "",
            "authors": authors,
            "organization": venue,
            "venue": venue,
            "year": year,
            "document_type": "Journal Article",
            "doi_or_url": doi,
            "pdf_url": pdf_url,
        })
    return papers


def extract_europepmc_pdf_url(result: dict[str, Any]) -> str:
    full_text_url_list = result.get("fullTextUrlList") or {}
    urls = full_text_url_list.get("fullTextUrl") or []
    if isinstance(urls, dict):
        urls = [urls]

    for item in urls:
        url = item.get("url", "")
        document_style = item.get("documentStyle", "").lower()
        if "pdf" in document_style or url.lower().endswith(".pdf") or "pdf" in url.lower():
            return url
    return ""


def search_europepmc(query: str, per_query: int, page: int = 1) -> list[dict[str, Any]]:
    params = {
        "query": f'({query}) OPEN_ACCESS:y',
        "format": "json",
        "pageSize": min(per_query, 100),
        "page": page,
    }
    response = requests.get(EUROPE_PMC_API_URL, params=params, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()
    results = data.get("resultList", {}).get("result", [])

    papers = []
    for item in results:
        title = normalize_space(item.get("title", ""))
        abstract = normalize_space(item.get("abstractText", ""))
        year = str(item.get("pubYear", "") or "")
        authors = normalize_space(item.get("authorString", "") or "")
        venue = normalize_space(item.get("journalTitle", "") or "Europe PMC")
        doi = item.get("doi") or item.get("pmcid") or item.get("id") or ""
        pdf_url = extract_europepmc_pdf_url(item)

        if not pdf_url:
            continue
        if not is_climate_related(title, abstract):
            continue

        papers.append({
            "source_api": "EuropePMC",
            "external_id": str(item.get("id") or item.get("pmcid") or stable_hash(title)),
            "title": title,
            "abstract": abstract,
            "authors": authors.replace(",", ";"),
            "organization": venue,
            "venue": venue,
            "year": year,
            "document_type": "Journal Article",
            "doi_or_url": doi,
            "pdf_url": pdf_url,
        })
    return papers


def download_pdf(url: str, output_path: Path) -> bool:
    if output_path.exists() and output_path.stat().st_size > 20_000:
        return True

    try:
        response = requests.get(url, headers=HEADERS, timeout=90, allow_redirects=True)
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get("content-type", "").lower()

        if not content.startswith(b"%PDF") and "pdf" not in content_type:
            return False

        output_path.write_bytes(content)
        time.sleep(0.5)
        return True
    except Exception:
        return False


def read_pdf_pages(pdf_path: Path) -> list[dict[str, Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append({"page_number": page_index, "text": text})
    return pages


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    text = normalize_space(text)
    if not text:
        return []

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if len(chunk) >= 100:
            chunks.append(chunk)
        start += step
    return chunks


def first_sentences(text: str, max_chars: int = 450) -> str:
    text = normalize_space(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    answer = " ".join(sentences[:2]) if sentences else text[:max_chars]
    return answer[:max_chars].strip()


def score_chunk_for_terms(chunk: dict[str, Any], terms: list[str]) -> int:
    text = chunk.get("text", "").lower()
    meta = " ".join(
        chunk.get("topics", [])
        + chunk.get("countries", [])
        + chunk.get("regions", [])
        + chunk.get("sectors", [])
        + chunk.get("climate_risks", [])
        + chunk.get("technologies", [])
        + chunk.get("policies", [])
        + chunk.get("targets", [])
        + chunk.get("indicators", [])
    ).lower()

    score = 0
    for term in terms:
        t = term.lower()
        score += text.count(t)
        score += 2 * meta.count(t)
    return score


def select_relevant_chunks(chunks: list[dict[str, Any]], terms: list[str], limit: int = 3) -> list[dict[str, Any]]:
    scored = []
    for chunk in chunks:
        score = score_chunk_for_terms(chunk, terms)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = []
    seen_docs = set()

    for _, chunk in scored:
        if chunk["document_id"] not in seen_docs:
            selected.append(chunk)
            seen_docs.add(chunk["document_id"])
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for _, chunk in scored:
            if chunk not in selected:
                selected.append(chunk)
            if len(selected) >= limit:
                break

    return selected[:limit]


def build_qa_item(qid: int, question: str, question_type: str, terms: list[str], chunks: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected = select_relevant_chunks(chunks, terms, limit=3)
    if not selected:
        return None

    required_entities = []
    for c in selected:
        required_entities.extend(
            c.get("topics", [])
            + c.get("countries", [])
            + c.get("regions", [])
            + c.get("sectors", [])
            + c.get("climate_risks", [])
            + c.get("technologies", [])
            + c.get("policies", [])
            + c.get("targets", [])
            + c.get("indicators", [])
        )

    return {
        "question_id": f"Q{qid:03d}",
        "question": question,
        "expected_answer": first_sentences(selected[0]["text"]),
        "question_type": question_type,
        "source_documents": sorted(set(c["document_id"] for c in selected)),
        "pages": [str(c["page_start"]) for c in selected],
        "required_entities": sorted(set(required_entities))[:12],
        "relevant_chunk_ids": [c["chunk_id"] for c in selected],
        "evidence": [
            {
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "title": c["title"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
            }
            for c in selected
        ],
        "needs_manual_review": True,
    }


def generate_retrieval_qa(chunks: list[dict[str, Any]], output_path: Path, target_questions: int) -> list[dict[str, Any]]:
    gold = []
    used_questions = set()
    qid = 1

    def add_question(question: str, qtype: str, terms: list[str]) -> None:
        nonlocal qid
        if len(gold) >= target_questions:
            return
        key = question.lower().strip()
        if key in used_questions:
            return
        item = build_qa_item(qid, question, qtype, terms, chunks)
        if item:
            gold.append(item)
            used_questions.add(key)
            qid += 1

    base_templates = [
        ("Which documents discuss renewable energy in relation to climate action?", "topic_lookup", ["renewable energy", "solar", "wind"]),
        ("How is machine learning used in climate-related research?", "technology", ["machine learning", "climate"]),
        ("Which papers discuss deep learning for climate or sustainability problems?", "technology", ["deep learning", "climate"]),
        ("Which documents discuss carbon emissions or emissions reduction?", "mitigation", ["carbon emissions", "emissions reduction"]),
        ("Which documents discuss greenhouse gas emissions?", "mitigation", ["greenhouse gas", "emissions"]),
        ("Which papers discuss solar energy forecasting?", "renewable_energy", ["solar", "forecasting"]),
        ("Which papers discuss wind energy forecasting?", "renewable_energy", ["wind", "forecasting"]),
        ("Which documents discuss climate adaptation or resilience?", "adaptation", ["adaptation", "resilience"]),
        ("Which documents discuss sea level rise or coastal risk?", "climate_risk", ["sea level", "coastal"]),
        ("Which documents discuss water scarcity under climate change?", "climate_risk", ["water scarcity", "climate"]),
        ("Which documents discuss agriculture or food security under climate change?", "sector", ["agriculture", "food security"]),
        ("Which documents discuss climate finance or investment?", "finance", ["climate finance", "investment"]),
        ("Which papers use remote sensing for climate analysis?", "method", ["remote sensing", "climate"]),
        ("Which papers use forecasting methods for climate or energy questions?", "method", ["forecasting", "energy"]),
        ("Which documents discuss net zero or energy transition?", "policy", ["net zero", "energy transition"]),
        ("Which documents discuss carbon capture as a mitigation technology?", "technology", ["carbon capture", "mitigation"]),
        ("Which documents discuss green hydrogen as a clean technology?", "technology", ["green hydrogen", "hydrogen"]),
        ("Which documents connect climate change with public health?", "health", ["health", "climate"]),
        ("Which documents discuss temperature rise or global warming?", "climate_science", ["temperature", "warming"]),
        ("Which documents discuss climate risk assessment?", "risk_reasoning", ["climate risk", "risk assessment"]),
        ("Which documents discuss sustainability and SDGs?", "sdgs", ["sustainability", "sdg"]),
        ("Which documents discuss policy and governance in climate action?", "policy_governance", ["policy", "governance"]),
    ]

    for question, qtype, terms in base_templates:
        add_question(question, qtype, terms)

    # Generate more questions from metadata-rich chunks until exactly target_questions.
    for chunk in chunks:
        if len(gold) >= target_questions:
            break

        title = chunk.get("title", "this document")
        page = chunk.get("page_start", "")

        for topic in chunk.get("topics", [])[:2]:
            add_question(f"What does '{title}' say about {topic}?", "document_topic", [topic, title])

        for tech in chunk.get("technologies", [])[:2]:
            add_question(f"Which evidence discusses {tech} and its climate relevance?", "technology_reasoning", [tech])

        for risk in chunk.get("climate_risks", [])[:2]:
            add_question(f"Which documents discuss {risk} as a climate risk?", "risk_reasoning", [risk])

        for sector in chunk.get("sectors", [])[:2]:
            add_question(f"How is the {sector} sector discussed in the climate evidence corpus?", "sector_reasoning", [sector])

        for country in chunk.get("countries", [])[:1]:
            add_question(f"What climate-related evidence is available for {country}?", "country_lookup", [country])

        for region in chunk.get("regions", [])[:1]:
            add_question(f"What climate evidence is available for the {region} region?", "region_lookup", [region])

        for indicator in chunk.get("indicators", [])[:1]:
            add_question(f"Which evidence discusses the indicator '{indicator}'?", "indicator_lookup", [indicator])

        text = chunk.get("text", "").lower()
        terms = []
        for possible in [
            "climate change", "emissions", "renewable energy", "machine learning",
            "temperature", "adaptation", "mitigation", "forecasting", "energy",
            "sustainability", "carbon"
        ]:
            if possible in text:
                terms.append(possible)

        if terms:
            add_question(
                f"What does page {page} of '{title}' say about {terms[0]}?",
                "page_grounded_fact",
                [terms[0], title],
            )

    # If still short, generate chunk-grounded questions.
    idx = 0
    while len(gold) < target_questions and chunks:
        chunk = chunks[idx % len(chunks)]
        title = chunk.get("title", "this document")
        page = chunk.get("page_start", "")

        question = f"What is the main climate-related evidence on page {page} of '{title}'? [auto-{len(gold)+1}]"

        item = {
            "question_id": f"Q{qid:03d}",
            "question": question,
            "expected_answer": first_sentences(chunk.get("text", "")),
            "question_type": "auto_chunk_grounded",
            "source_documents": [chunk.get("document_id", "")],
            "pages": [str(page)],
            "required_entities": sorted(set(
                chunk.get("topics", [])
                + chunk.get("countries", [])
                + chunk.get("regions", [])
                + chunk.get("sectors", [])
                + chunk.get("climate_risks", [])
                + chunk.get("technologies", [])
                + chunk.get("policies", [])
                + chunk.get("targets", [])
                + chunk.get("indicators", [])
            ))[:12],
            "relevant_chunk_ids": [chunk.get("chunk_id", "")],
            "evidence": [
                {
                    "chunk_id": chunk.get("chunk_id", ""),
                    "document_id": chunk.get("document_id", ""),
                    "title": title,
                    "page_start": page,
                    "page_end": chunk.get("page_end", ""),
                }
            ],
            "needs_manual_review": True,
        }

        gold.append(item)
        qid += 1
        idx += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(gold[:target_questions], indent=2, ensure_ascii=False), encoding="utf-8")

    return gold[:target_questions]


def save_outputs(
    metadata_rows: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    metadata_out: Path,
    chunks_out: Path,
) -> None:
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metadata_rows).to_csv(metadata_out, index=False, encoding="utf-8-sig")

    chunks_out.parent.mkdir(parents=True, exist_ok=True)
    chunks_out.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")


def build_dataset(
    target_pdfs: int,
    per_query: int,
    pdf_dir: Path,
    metadata_out: Path,
    chunks_out: Path,
    qa_out: Path,
    report_out: Path,
    qa_questions: int,
    mailto: str | None,
) -> None:
    pdf_dir.mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    chunks = []
    errors = []
    seen_candidates = set()
    used_document_ids = set()
    chunk_counter = 1

    print(f"[INFO] Target: exactly {target_pdfs} successfully processed PDFs")
    print("[INFO] Failed PDFs will be skipped and replaced by other candidates.")
    print("[INFO] No max chunk limit is used.\n")

    max_rounds = 25

    for round_i in range(max_rounds):
        if len(metadata_rows) >= target_pdfs:
            break

        print(f"\n========== SEARCH ROUND {round_i + 1}/{max_rounds} ==========")

        for query in SEARCH_QUERIES:
            if len(metadata_rows) >= target_pdfs:
                break

            search_jobs = [
                ("arXiv", lambda: search_arxiv(query, per_query, start=round_i * per_query)),
                ("OpenAlex", lambda: search_openalex(query, per_query, page=round_i + 1, mailto=mailto)),
                ("EuropePMC", lambda: search_europepmc(query, per_query, page=round_i + 1)),
            ]

            for source_name, search_func in search_jobs:
                if len(metadata_rows) >= target_pdfs:
                    break

                print(f"[SEARCH] {source_name}: {query}")

                try:
                    candidates = search_func()
                except Exception as e:
                    print(f"[WARNING] Search failed: {source_name} / {query} / {e}")
                    continue

                for paper in tqdm(candidates, desc=f"Processing {source_name}", leave=False):
                    if len(metadata_rows) >= target_pdfs:
                        break

                    candidate_key = unique_key_for_paper(paper)
                    if candidate_key in seen_candidates:
                        continue
                    seen_candidates.add(candidate_key)

                    doc_number = make_doc_number(len(metadata_rows) + 1)
                    base_document_id = make_document_id(paper)
                    document_id = base_document_id

                    suffix = 2
                    while document_id in used_document_ids:
                        document_id = f"{base_document_id}_{suffix}"
                        suffix += 1
                    used_document_ids.add(document_id)

                    pdf_path = pdf_dir / f"{document_id}.pdf"

                    if not download_pdf(paper["pdf_url"], pdf_path):
                        errors.append({
                            "document_id": document_id,
                            "title": paper.get("title", ""),
                            "pdf_url": paper.get("pdf_url", ""),
                            "source_api": paper.get("source_api", ""),
                            "error": "download_failed_or_not_pdf",
                        })
                        continue

                    try:
                        pages = read_pdf_pages(pdf_path)
                    except Exception as e:
                        errors.append({
                            "document_id": document_id,
                            "title": paper.get("title", ""),
                            "pdf_path": str(pdf_path),
                            "source_api": paper.get("source_api", ""),
                            "error": f"pdf_open_or_extract_failed: {e}",
                        })
                        continue

                    sample_text = normalize_space(
                        paper.get("title", "")
                        + " "
                        + paper.get("abstract", "")
                        + " "
                        + " ".join(p["text"] for p in pages[:2])
                    )
                    doc_meta = infer_metadata_from_text(sample_text)

                    document_chunks = []

                    for page in pages:
                        page_text = normalize_space(page["text"])
                        if not page_text:
                            continue

                        for chunk in chunk_text(page_text):
                            chunk_meta = infer_metadata_from_text(chunk)

                            document_chunks.append({
                                "chunk_id": f"chunk_{chunk_counter + len(document_chunks):06d}",
                                "doc_number": doc_number,
                                "document_id": document_id,
                                "title": paper.get("title", ""),
                                "text": chunk,
                                "page_start": page["page_number"],
                                "page_end": page["page_number"],
                                "topics": chunk_meta["topics"] or doc_meta["topics"],
                                "countries": chunk_meta["countries"] or doc_meta["countries"],
                                "regions": chunk_meta["regions"] or doc_meta["regions"],
                                "sectors": chunk_meta["sectors"] or doc_meta["sectors"],
                                "climate_risks": chunk_meta["climate_risks"] or doc_meta["climate_risks"],
                                "technologies": chunk_meta["technologies"] or doc_meta["technologies"],
                                "policies": chunk_meta["policies"] or doc_meta["policies"],
                                "targets": chunk_meta["targets"] or doc_meta["targets"],
                                "indicators": chunk_meta["indicators"] or doc_meta["indicators"],
                            })

                    if not document_chunks:
                        errors.append({
                            "document_id": document_id,
                            "title": paper.get("title", ""),
                            "pdf_path": str(pdf_path),
                            "source_api": paper.get("source_api", ""),
                            "error": "no_text_chunks_extracted",
                        })
                        continue

                    metadata_rows.append({
                        "doc_number": doc_number,
                        "document_id": document_id,
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", ""),
                        "organization": paper.get("organization", ""),
                        "venue": paper.get("venue", ""),
                        "year": paper.get("year", ""),
                        "document_type": paper.get("document_type", ""),
                        "pdf_path": str(pdf_path).replace("\\", "/"),
                        "doi_or_url": paper.get("doi_or_url", ""),
                        "pdf_url": paper.get("pdf_url", ""),
                        "source_api": paper.get("source_api", ""),
                        "external_id": paper.get("external_id", ""),
                        "total_pages": len(pages),
                        "topics": join_values(doc_meta["topics"]),
                        "countries": join_values(doc_meta["countries"]),
                        "regions": join_values(doc_meta["regions"]),
                        "sectors": join_values(doc_meta["sectors"]),
                        "climate_risks": join_values(doc_meta["climate_risks"]),
                        "technologies": join_values(doc_meta["technologies"]),
                        "policies": join_values(doc_meta["policies"]),
                        "targets": join_values(doc_meta["targets"]),
                        "indicators": join_values(doc_meta["indicators"]),
                        "abstract": paper.get("abstract", ""),
                    })

                    chunks.extend(document_chunks)
                    chunk_counter += len(document_chunks)

                    print(f"[OK] {len(metadata_rows)}/{target_pdfs}: {document_id}")

                    # Save progress every 10 successful PDFs.
                    if len(metadata_rows) % 10 == 0:
                        save_outputs(metadata_rows, chunks, metadata_out, chunks_out)

                time.sleep(1)

    if len(metadata_rows) < target_pdfs:
        save_outputs(metadata_rows, chunks, metadata_out, chunks_out)
        raise RuntimeError(
            f"Could not reach exactly {target_pdfs} processed PDFs. "
            f"Processed only {len(metadata_rows)}. "
            f"Run again, increase --per-query, or add more search queries."
        )

    # Keep exactly target_pdfs in case of over-collection.
    metadata_rows = metadata_rows[:target_pdfs]
    valid_doc_ids = {row["document_id"] for row in metadata_rows}
    chunks = [c for c in chunks if c["document_id"] in valid_doc_ids]

    save_outputs(metadata_rows, chunks, metadata_out, chunks_out)

    qa_items = generate_retrieval_qa(
        chunks=chunks,
        output_path=qa_out,
        target_questions=qa_questions,
    )

    source_counts = {}
    venue_counts = {}
    for row in metadata_rows:
        source_counts[row["source_api"]] = source_counts.get(row["source_api"], 0) + 1
        venue = row.get("venue") or "Unknown"
        venue_counts[venue] = venue_counts.get(venue, 0) + 1

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_pdfs": target_pdfs,
        "downloaded_and_processed_pdfs": len(metadata_rows),
        "total_chunks": len(chunks),
        "qa_questions": len(qa_items),
        "metadata_out": str(metadata_out),
        "chunks_out": str(chunks_out),
        "qa_out": str(qa_out),
        "pdf_dir": str(pdf_dir),
        "source_counts": source_counts,
        "top_venues": dict(sorted(venue_counts.items(), key=lambda x: x[1], reverse=True)[:30]),
        "errors_count": len(errors),
        "errors_sample": errors[:300],
        "warnings": [],
        "important_note": "Q/A is automatically generated for retrieval evaluation and must be manually reviewed.",
    }

    if len(qa_items) < qa_questions:
        report["warnings"].append(
            f"Requested {qa_questions} Q/A items but generated {len(qa_items)}."
        )

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n[DONE]")
    print(f"PDF folder      : {pdf_dir}")
    print(f"Metadata CSV    : {metadata_out}")
    print(f"Chunks JSON     : {chunks_out}")
    print(f"Q/A JSON        : {qa_out}")
    print(f"Report JSON     : {report_out}")
    print(f"Processed PDFs  : {len(metadata_rows)}")
    print(f"Total chunks    : {len(chunks)}")
    print(f"Q/A questions   : {len(qa_items)}")
    print(f"Errors          : {len(errors)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect exactly 300 open-access climate PDFs and build D1 retrieval data."
    )

    parser.add_argument("--target-pdfs", type=int, default=300)
    parser.add_argument("--per-query", type=int, default=100)
    parser.add_argument("--qa-questions", type=int, default=300)
    parser.add_argument("--pdf-dir", default="data/pdfs")
    parser.add_argument("--metadata-out", default="data/metadata/papers_metadata.csv")
    parser.add_argument("--chunks-out", default="data/sample/sample_chunks.json")
    parser.add_argument("--qa-out", default="data/gold/d1_retrieval_eval_set.json")
    parser.add_argument("--report-out", default="data/sample/dataset_validation_report.json")
    parser.add_argument("--mailto", default=None)

    args = parser.parse_args()

    build_dataset(
        target_pdfs=args.target_pdfs,
        per_query=args.per_query,
        pdf_dir=Path(args.pdf_dir),
        metadata_out=Path(args.metadata_out),
        chunks_out=Path(args.chunks_out),
        qa_out=Path(args.qa_out),
        report_out=Path(args.report_out),
        qa_questions=args.qa_questions,
        mailto=args.mailto,
    )


if __name__ == "__main__":
    main()