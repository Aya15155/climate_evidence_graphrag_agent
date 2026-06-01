# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: log prequential accuracy and ADWIN drift alerts for the D1 report plot.
# - Improvement: connect feedback labels to hybrid weight adaptation after the first working retrieval baseline.
# ------------------------------------------------------------
self.topic_priors = {
    "policy_governance": 0.65,
    "uae_cop28": 0.65,
    "mitigation": 0.55,
    "adaptation": 0.50,
    "climate_science": 0.40,
    "technology_innovation": 0.40,
    "global": default_bm25_weight,
}
