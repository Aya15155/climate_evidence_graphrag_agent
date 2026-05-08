# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: keep this starter file small, tested, and connected to the final integrated pipeline.
# ------------------------------------------------------------
from src.rag.graphrag_executor import extract_climate_entities

def test_extract_entities():
    entities = extract_climate_entities('Which UAE policies discuss renewable energy?')
    assert 'UAE' in entities['countries']
    assert 'renewable energy' in [x.lower() for x in entities['technologies']]
