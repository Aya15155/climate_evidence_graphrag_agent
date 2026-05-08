# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: run QLoRA only after the retrieval pipeline is stable and gold Q/A examples are validated.
# - Improvement: compare tuned vs zero-shot answers using faithfulness, relevance, latency, and citation correctness.
# ------------------------------------------------------------
def build_instruction_sample(context: str, question: str, answer: str) -> dict:
    return {
        "instruction": "Answer using only the provided climate evidence and cite document/page sources.",
        "context": context,
        "question": question,
        "answer": answer,
    }
