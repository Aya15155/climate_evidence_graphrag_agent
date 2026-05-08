# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: log prequential accuracy and ADWIN drift alerts for the D1 report plot.
# - Improvement: connect feedback labels to hybrid weight adaptation after the first working retrieval baseline.
# - Improvement: expand the stream to 500 labeled/augmented climate queries and annotate the drift point in the plot.
# ------------------------------------------------------------
CLIMATE_TOPICS = ["mitigation", "adaptation", "policy", "climate_science", "technology", "uae_cop28"]

class RiverTopicClassifier:
    """Aaya owns this file for D1.

    Online model for query -> climate topic classification.
    """
    def __init__(self):
        from river import compose, feature_extraction, naive_bayes
        self.model = compose.Pipeline(
            feature_extraction.BagOfWords(lowercase=True),
            naive_bayes.MultinomialNB(),
        )

    def predict(self, query: str):
        return self.model.predict_one(query)

    def learn(self, query: str, topic: str) -> None:
        self.model.learn_one(query, topic)
