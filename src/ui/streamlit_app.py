# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: show retrieved evidence, graph path, citations, page ranges, and safety status in the UI.
# - Improvement: add feedback buttons that post to /feedback for River adaptation.
# ------------------------------------------------------------
import streamlit as st

st.set_page_config(page_title="Climate Evidence GraphRAG Agent", layout="wide")
st.title("Climate Evidence GraphRAG Agent")
st.caption("Climate-specific GraphRAG with citations, safety, online learning, and QLoRA tuning.")

question = st.text_input("Ask a climate evidence question", "Which UAE climate policies address renewable energy targets?")
if st.button("Ask"):
    st.info("Connect this UI to FastAPI /ask. The final answer should show citations and page ranges.")
    st.write({"question": question, "answer": "TODO", "citations": []})

with st.expander("Architecture"):
    st.image("docs/architecture_graph.png")
with st.expander("Climate Evidence Knowledge Graph"):
    st.image("docs/climate_evidence_kg_graph.png")
