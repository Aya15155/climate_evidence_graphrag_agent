# Climate Evidence GraphRAG Agent

A trusted AI assistant for climate policy, sustainability, climate science, and climate-AI research PDFs.

This project is **not just a PDF reader**. PDFs are the evidence sources, while the core intelligence comes from a **Climate Evidence Knowledge Graph** that connects countries, policies, climate risks, sectors, technologies, targets, indicators, findings, organizations, and source documents.

## What is included in this zip

```text
src/                  Python starter code for ingestion, retrieval, graph, GraphRAG, learning, tuning, safety, API, UI, and evaluation
tests/                Smoke tests for the starter pipeline
configs/              Main config and D1 run card template
data/                 Metadata, gold Q/A, and fine-tuning templates
docs/                 Word plan + architecture graph + climate knowledge graph
reports/              Member report-section templates and final-report outline
notes/                Improvement notes and file-by-file comments
README.md             Setup, run steps, member ownership, and deliverable map
```

Every Python file in `src/` and `tests/` now includes **inline improvement comments** at the top. These comments explain what should be upgraded before submission.

## Project idea

The user asks a climate question, such as:

- Which UAE climate policies address renewable energy targets?
- Which climate risks affect agriculture in the Middle East?
- Which documents discuss green hydrogen as a mitigation technology?
- What climate impacts are linked to sea level rise?
- Which AI methods are used in climate forecasting papers?

The system should:

1. Extract climate entities from the question.
2. Search Neo4j for connected climate concepts and evidence documents.
3. Retrieve supporting chunks using BM25 + dense Qdrant search.
4. Blend graph-guided results with global hybrid retrieval.
5. Generate an answer with document/page citations.
6. Verify citations using source pinning.
7. Learn from feedback using River + ADWIN.

## Architecture and graph diagrams

- Architecture graph: `docs/architecture_graph.png`
- Climate Evidence Knowledge Graph: `docs/climate_evidence_kg_graph.png`
- Updated Word plan with the first design style: `docs/Climate_Project_Plan_First_Design_UPDATED.docx`

## Team members and ownership

| Member | Name | Main role |
|---|---|---|
| Member 1 | Reem | Data, ingestion, gold Q/A, page citation verification |
| Member 2 | Salma | Retrieval, hybrid search, AutoML, retrieval evaluation |
| Member 3 | Rana | Climate Evidence Knowledge Graph and GraphRAG |
| Member 4 | Aaya | Online learning, ADWIN drift, feedback adaptation, QLoRA |
| Member 5 | Alia | API, UI, safety, evaluation, README, report compilation |

Each member writes their own report section. Alia may compile the final report, but she should not write everyone else’s technical work.

## Deliverables and highlighted files

### D1 — Streaming Learner and AutoML

- Reem: `data/metadata/papers_metadata_template.csv`, `data/gold/gold_qa_set_template.json`, `reports/member1_d1_data_section.md`
- Salma: `src/retrieval/automl_tuner.py`, `configs/run_card_d1.yaml`, `reports/member2_d1_automl_section.md`
- Rana: `src/graph/graph_schema.md`, `reports/member3_d1_graph_plan_section.md`
- Aaya: `src/learning/river_topic_classifier.py`, `src/learning/drift_detector.py`, `reports/member4_d1_online_learning_section.md`
- Alia: `src/evaluation/retrieval_metrics.py`, `reports/member5_d1_eval_section.md`

### D2 — Retrieval Stack and Graph Build

- Reem: `src/ingest/pdf_loader.py`, `src/ingest/chunker.py`, `src/ingest/mongo_store.py`, `src/ingest/qdrant_store.py`, `src/ingest/run_ingest.py`
- Salma: `src/retrieval/bm25_retriever.py`, `src/retrieval/dense_retriever.py`, `src/retrieval/hybrid_retriever.py`, `src/retrieval/fusion.py`
- Rana: `src/graph/neo4j_builder.py`, `src/graph/cypher_queries.py`, `src/graph/graph_schema.md`, `docs/climate_evidence_kg_graph.png`
- Aaya: `src/learning/feedback_adapter.py`
- Alia: `src/api/main.py`, `docs/architecture_graph.png`, `reports/member5_d2_api_eval_section.md`

### D3 — GraphRAG, Evaluation, and Safety

- Reem: `src/ingest/page_verifier.py`, `reports/member1_d3_data_quality_section.md`
- Salma: `src/evaluation/retrieval_metrics.py`, `reports/tables/d3_retrieval_ablation.csv`
- Rana: `src/rag/graphrag_executor.py`, `src/rag/prompt_builder.py`, `src/rag/citation_builder.py`
- Aaya: `src/learning/feedback_adapter.py`, `reports/member4_d3_adaptation_section.md`
- Alia: `src/safety/source_pinning.py`, `src/safety/citation_verifier.py`, `src/evaluation/rag_metrics.py`, `src/evaluation/ablation.py`

### D4 — SLM Tuning and Final Demo

- Reem: `data/tuning/finetune_qa_template.jsonl`, `reports/member1_d4_dataset_section.md`
- Salma: `src/evaluation/latency.py`, `reports/tables/d4_retrieval_latency.csv`
- Rana: `src/rag/graphrag_executor.py`, `src/graph/cypher_queries.py`, `reports/member3_d4_graph_final_section.md`
- Aaya: `src/tuning/prepare_finetune_data.py`, `src/tuning/finetune_qlora.py`, `src/tuning/inference_tuned.py`, `reports/tuning_card.md`
- Alia: `src/ui/streamlit_app.py`, `tests/`, `README.md`, `demo_script.md`, `reports/final_report_outline.md`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Start databases

```bash
docker compose up -d
```

This starts:

- MongoDB on port 27017
- Qdrant on port 6333
- Neo4j on ports 7474 and 7687

## Run ingestion

Put PDFs in `data/pdfs/`, fill `data/metadata/papers_metadata_template.csv`, then run:

```bash
python -m src.ingest.run_ingest
```

## Run API

```bash
uvicorn src.api.main:app --reload
```

Endpoints:

- `GET /stats`
- `POST /ingest`
- `POST /search`
- `POST /ask`
- `POST /feedback`

## Run UI

```bash
streamlit run src/ui/streamlit_app.py
```

## Run tests

```bash
pytest tests/ -v
```

## Notes for improvement

See:

- `notes/improvements.md`
- `notes/code_improvement_comments.md`
- the improvement comments at the top of each Python file

## Important safety rule

The answer generator must answer only from retrieved evidence. If the retrieved chunks do not support a claim, the answer should say that the evidence is not available in the document set. This is especially important for climate claims, statistics, COP commitments, and policy targets.
