import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def tfidf_vector(text: str, corpus_vocab: dict[str, int], doc_count: int) -> dict[str, float]:
    tokens = tokenize(text)
    tf = Counter(tokens)
    total = len(tokens) or 1
    vec: dict[str, float] = {}
    for term, count in tf.items():
        idf = math.log((doc_count + 1) / (corpus_vocab.get(term, 0) + 1)) + 1
        vec[term] = (count / total) * idf
    return vec


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in set(a) | set(b))
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def simple_embed(text: str, dims: int = 64) -> list[float]:
    """Deterministic hash-based embedding for dev without API keys."""
    vec = [0.0] * dims
    for token in tokenize(text):
        h = hash(token)
        idx = abs(h) % dims
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embedding_cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
