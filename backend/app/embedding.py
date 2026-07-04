"""Deterministic embeddings for semantic retrieval without an external model.

Hashes tokens into a fixed-dimension bag-of-words vector with sublinear term
weighting, L2-normalized for cosine similarity. This is a real, dependency-free
vector index. When QDRANT_URL / a real embedding model is configured, the same
`embed()` contract is swapped for model embeddings + Qdrant search.
"""
from __future__ import annotations

import hashlib
import math
import re

DIM = 256
_STOP = set(
    "a an the and or but if of to in on for with at by from is are was were be been being we our us i you they it this that these those as into about over".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9$%.]+", text.lower()) if len(t) > 1 and t not in _STOP]


def _stable_hash(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode()).digest()[:4], "big")


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    counts: dict[str, int] = {}
    for tok in tokenize(text):
        counts[tok] = counts.get(tok, 0) + 1
    for tok, c in counts.items():
        idx = _stable_hash(tok) % DIM
        vec[idx] += 1.0 + math.log(c)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
