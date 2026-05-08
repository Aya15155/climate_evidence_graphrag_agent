# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: test fake climate statistics, fake COP commitments, and prompt-injection attempts.
# - Improvement: refuse unsupported answers when retrieved chunks do not contain enough evidence.
# ------------------------------------------------------------
RISKY_PHRASES = ["ignore previous instructions", "do not cite", "make up", "invent", "bypass"]


def has_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in RISKY_PHRASES)
