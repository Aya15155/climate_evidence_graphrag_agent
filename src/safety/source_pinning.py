# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: test fake climate statistics, fake COP commitments, and prompt-injection attempts.
# - Improvement: refuse unsupported answers when retrieved chunks do not contain enough evidence.
# ------------------------------------------------------------
def enforce_source_pinning(answer: str, retrieved_chunks: list[dict]) -> str:
    """Reject unsupported answers when no retrieved evidence exists."""
    if not retrieved_chunks:
        return "I could not find enough support in the uploaded climate documents."
    return answer
