"""
Lightweight policy retrieval -- pure Python, no compiled dependencies.

We chunk the policy markdown by section (## headers) and retrieve the
top-matching chunks for a query using simple TF-IDF-style keyword
scoring implemented by hand. No embedding API call and no scikit-learn
build step needed -> stays on the free tier, works offline, and avoids
the "no prebuilt wheel for this Python version" problem entirely.

This is deliberately NOT the LLM's general knowledge -- search_policy()
is the only source of policy text the agent is allowed to quote from,
and the system prompt instructs the model to only answer policy
questions using what this function returns.
"""
import re
import math
from collections import Counter
from pathlib import Path

POLICY_PATH = Path(__file__).parent.parent / "data" / "trendly_policy.md"

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "but", "if", "then",
    "this", "that", "these", "those", "it", "its", "with", "as", "at",
    "by", "from", "do", "does", "did", "can", "could", "will", "would",
    "should", "my", "i", "you", "your", "me", "we", "our", "have", "has",
    "had", "not", "no", "so", "what", "when", "where", "how", "which",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def _chunk_markdown(text: str):
    """Split into (heading, body) chunks on '##' headers. Falls back to
    the whole doc as one chunk if no headers are found."""
    parts = re.split(r"\n(?=## )", text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n")
        heading = lines[0].lstrip("#").strip() if lines[0].startswith("#") else "Policy"
        chunks.append({"heading": heading, "text": part})
    return chunks if chunks else [{"heading": "Policy", "text": text}]


class PolicyStore:
    def __init__(self, path: Path = POLICY_PATH):
        self.raw_text = path.read_text(encoding="utf-8")
        self.chunks = _chunk_markdown(self.raw_text)
        self._doc_tokens = [_tokenize(c["text"]) for c in self.chunks]
        self._doc_term_counts = [Counter(toks) for toks in self._doc_tokens]

        # IDF across chunks
        n_docs = len(self.chunks)
        df = Counter()
        for toks in self._doc_tokens:
            for term in set(toks):
                df[term] += 1
        self._idf = {term: math.log((n_docs + 1) / (count + 1)) + 1 for term, count in df.items()}

    def _score(self, query_tokens: list[str], doc_index: int) -> float:
        counts = self._doc_term_counts[doc_index]
        doc_len = max(len(self._doc_tokens[doc_index]), 1)
        score = 0.0
        for term in query_tokens:
            if term in counts:
                tf = counts[term] / doc_len
                idf = self._idf.get(term, math.log(len(self.chunks) + 1) + 1)
                score += tf * idf
        return score

    def search(self, query: str, top_k: int = 3, min_score: float = 0.01):
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scored = [(self._score(q_tokens, i), c) for i, c in enumerate(self.chunks)]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [c for score, c in scored[:top_k] if score >= min_score]
        return results


_store = None


def get_store() -> PolicyStore:
    global _store
    if _store is None:
        _store = PolicyStore()
    return _store
