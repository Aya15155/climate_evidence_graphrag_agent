# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: run QLoRA only after the retrieval pipeline is stable and gold Q/A examples are validated.
# - Improvement: compare tuned vs zero-shot answers using faithfulness, relevance, latency, and citation correctness.
# ------------------------------------------------------------
class TunedModelInference:
    def __init__(self, model_path: str = "models/tuned"):
        self.model_path = model_path

    def generate(self, prompt: str) -> str:
        return "TODO: load quantized QLoRA model and generate answer."
