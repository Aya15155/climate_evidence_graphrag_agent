# Code Improvement Comments by File Group

This file summarizes the inline improvement comments added to the Python files.

## Ingestion files: `src/ingest/`

Improve PDF robustness, page mapping, scanned-PDF handling, metadata validation, and citation page verification. Reem should make sure every chunk keeps `document_id`, `title`, `start_page`, `end_page`, `countries`, `sectors`, `policies`, `technologies`, `climate_risks`, and `indicators`.

## Retrieval files: `src/retrieval/`

Replace placeholders with real BM25 and Qdrant retrieval. Salma should evaluate BM25-only, dense-only, fixed hybrid, and AutoML-tuned hybrid using Recall@5, NDCG@5, MRR, and p95 latency.

## Graph files: `src/graph/`

Keep the graph climate-specific. Rana should create nodes for `Document`, `Country`, `Region`, `Policy`, `Target`, `ClimateTopic`, `ClimateRisk`, `Sector`, `Technology`, `Method`, `Finding`, `Indicator`, `Organization`, `Author`, and `Venue`.

## RAG files: `src/rag/`

The GraphRAG executor should extract climate entities, run Cypher, retrieve graph-linked documents, blend graph-guided chunks with global retrieval, and return answer traces with citations and page ranges.

## Learning files: `src/learning/`

Aaya should simulate a query stream, inject drift, produce the prequential accuracy plot, and connect helpful/not-helpful feedback to the adaptive hybrid strategy.

## Tuning files: `src/tuning/`

Aaya should run QLoRA only when the gold Q/A examples are ready. The final report must include a tuning card with model, dataset size, epochs, learning rate, LoRA rank, hardware, training time, quantization, and license.

## Safety files: `src/safety/`

Alia should test fake climate statistics, fake COP commitments, prompt injection, unsupported answers, and citations that do not match retrieved chunks.

## Evaluation files: `src/evaluation/`

Use the same gold Q/A set across D1-D4. Report retrieval metrics, RAG faithfulness/relevance, hallucinated citation rate, safety before/after evidence, and p95 latency.

## API/UI files: `src/api/`, `src/ui/`

Alia should show answer, citations, page ranges, retrieved chunks, graph path, safety status, and feedback buttons in the demo.
