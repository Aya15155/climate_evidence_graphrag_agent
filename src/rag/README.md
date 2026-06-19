# D3 RAG Module Placeholder

Expected files for D3 implementation:

- `graphrag_executor.py` ? query -> Cypher subgraph -> supporting chunks -> blended retrieval -> answer trace.
- `prompt_builder.py` ? builds grounded answer prompts from chunks and graph paths.
- `citation_builder.py` ? formats and validates document/page citations.

Do not put secrets or live Neo4j credentials in code. Use environment variables.
