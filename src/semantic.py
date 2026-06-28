"""
Lightweight local semantic similarity using TF-IDF + Truncated SVD (LSA).

Why TF-IDF/LSA instead of a transformer embedding model:
  - The compute spec is hard: <=5 min wall-clock, <=16GB RAM, CPU-only, no
    network, for 100,000 candidates. Loading a sentence-transformer model and
    running it over 100K career-history texts on CPU is, by itself, a
    meaningful chunk of that 5-minute budget -- before any scoring logic runs.
  - The JD explicitly rewards exactly this kind of latency-quality tradeoff
    thinking: "running an LLM call for each of 100,000 candidates will not
    fit the 5-minute CPU budget ... plan for a small ranker over precomputed
    features, indexes, or compact local models."
  - Resume/JD text lives in a fairly constrained professional vocabulary,
    which is precisely the regime where TF-IDF + LSA performs well relative
    to its cost, and it keeps the system fully inspectable -- we can show
    exactly which terms drove a similarity score, which matters for the
    defend-your-work interview.
  - No heavy dependency (torch) is required; sklearn is sufficient.

This module fits a single shared TF-IDF + SVD space over (JD text + all
candidate career-history texts) and returns cosine similarity between the JD
and each candidate as a 0-1-ish score.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize


def build_semantic_index(jd_text: str, candidate_texts: list[str], n_components: int = 150):
    """
    Fits TF-IDF + truncated SVD over [jd_text] + candidate_texts.
    Returns (jd_vector, candidate_matrix) as L2-normalized dense arrays so that
    a dot product gives cosine similarity directly.
    """
    corpus = [jd_text] + candidate_texts

    vectorizer = TfidfVectorizer(
        max_features=20000,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.6,
        stop_words="english",
        sublinear_tf=True,
    )
    tfidf = vectorizer.fit_transform(corpus)

    n_components = min(n_components, tfidf.shape[1] - 1, tfidf.shape[0] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    reduced = svd.fit_transform(tfidf)
    reduced = normalize(reduced)

    jd_vector = reduced[0]
    candidate_matrix = reduced[1:]
    return jd_vector, candidate_matrix, vectorizer, svd


def semantic_similarity(jd_vector: np.ndarray, candidate_matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity (vectors already normalized) -> array in roughly [-1, 1], clipped to [0, 1]."""
    sims = candidate_matrix @ jd_vector
    return np.clip(sims, 0.0, 1.0)
